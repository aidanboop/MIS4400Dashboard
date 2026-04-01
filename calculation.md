# Calculation Reference — results.csv Columns

This document explains how each column in `results.csv` is calculated.

---

## Identity Columns

| Column | Description |
|--------|-------------|
| `StoreID` | Unique store identifier from `[Final].[Stores]` |
| `FiscalYearID` | Fiscal year (e.g. 2023, 2024) |
| `CalendarID` | Fiscal period within the year (01–13) |

---

## `flags`

**Source:** `flags/rules.py` — `compute_flags()`

A semicolon-separated list of rule names that fired for the given store/period. Empty when no rules triggered. Each rule compares a ratio or change metric against a configured threshold (defined in `config.py`).

### Rules

| Rule Name | Metric | Condition | Threshold | Severity |
|-----------|--------|-----------|-----------|----------|
| `low_gross_profit` | Gross Profit % of Product Sales | Below minimum | 55% | Critical |
| `high_labor_cost` | Labor % of Product Sales | Above maximum | 35% | Warning |
| `low_controllable_profit` | Profit After Controllable % of Product Sales | Below minimum | 10% | Critical |
| `low_cash_flow` | Restaurant Cash Flow % of Product Sales | Below minimum | 5% | Critical |
| `sales_decline` | Period-over-period Sales change % | Below threshold | -5% | Warning |

### How the ratios are calculated

All percentage ratios use **Account 10 (Product Sales)** as the denominator:

```
ratio = Account Amount / Product Sales (Account 10)
```

For example:
- **Gross Profit %** = Account 60 (Gross Profit) / Account 10 (Product Sales)
- **Labor %** = Account 110 (Labor) / Account 10 (Product Sales)
- **Profit After Controllable %** = Account 240 / Account 10
- **Restaurant Cash Flow %** = Account 450 / Account 10

### How Sales Decline % is calculated

```
sales_change_pct = (Current Period Sales - Previous Period Sales) / |Previous Period Sales|
```

"Previous period" is the prior `CalendarID` within the same `FiscalYearID` and `StoreID`. Period 01 has no prior period and is never flagged for decline.

### How derived accounts are computed

Accounts like Gross Profit (60), Labor (110), and Restaurant Cash Flow (450) are **not stored directly** in `MainData`. They are computed from their source accounts using rules in `[Final].[AccountCalc]`:

```
Derived Account Value = SUM(Source Account Amount * Multiplier)
```

For each `DestAccountID`, the system looks up all `(SourceAccountID, Multiplier)` rows in `AccountCalc` and sums the products. For example, Gross Profit (60) = Product Sales (10) * 1 + Cost of Sales (50) * -1.

---

## `is_at_risk`

**Source:** `flags/rules.py`

Boolean (`True` / `False`). Set to `True` if **any** flag rule triggered for that store/period, `False` otherwise.

---

## `predicted_sales`

**Source:** `models/predictor.py` — `predict_sales()`

The model's predicted Sales amount (in dollars) for the store/period.

**Model:** `RandomForestRegressor` (200 trees, scikit-learn)

**Training target:** The `Sales` column from `[Final].[POSSales]`

**Features used:** All numeric columns from the feature matrix, which includes:
- Raw account amounts (`acct_10`, `acct_20`, etc.) pivoted from `MainData`
- Derived/calculated accounts (`acct_60`, `acct_110`, `acct_240`, `acct_450`, etc.) computed via `AccountCalc` rules
- Percentage-of-sales ratios (`acct_60_pct`, `acct_110_pct`, etc.)
- Lag features: `acct_10_lag1` (prior period Product Sales), `Sales_lag1` (prior period POS Sales)
- Change features: `acct_10_chg` (period-over-period change in Product Sales), `Sales_chg` (period-over-period change in POS Sales)

**Pipeline:** Missing values are imputed with the median, then all features are standard-scaled before being passed to the model.

---

## `risk_label`

**Source:** `models/predictor.py` — `predict_risk()`

Integer classification label: `0` = healthy, `1` = at-risk.

**Model:** `GradientBoostingClassifier` (200 trees, scikit-learn)

**Training target:** Derived from the flag rules themselves — a store/period is labeled `1` if `compute_flags()` returns `is_at_risk = True` for it (i.e., any flag fired), and `0` otherwise. This means the ML model learns to predict whether a store/period *would* trigger rule-based flags, enabling it to generalize the pattern to new data.

**Features:** Same numeric feature set as the sales forecaster (account amounts, ratios, lags, changes), excluding `Sales` and ID columns.

**Pipeline:** Same as sales forecaster (median imputation, standard scaling).

---

## `risk_probability`

**Source:** `models/predictor.py` — `predict_risk_proba()`

The model's predicted probability (0.0 to 1.0) that the store/period is at-risk (class = 1). This is the GradientBoostingClassifier's `predict_proba` output for the positive class.

Stores with `risk_probability >= 0.60` (60%) are marked as **HIGH RISK** in the CLI report output.
