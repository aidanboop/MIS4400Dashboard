# Backend Architecture & How It Works

This document explains how the Python backend is structured, how each layer fits together, and how data flows from the SQL Server database through the ML pipeline to the React frontend.

---

## High-Level Overview

```
SQL Server [Final schema]
        |
        | pyodbc
        v
   db/queries.py       ← pulls MainData, POSSales, Accounts, etc.
        |
        v
models/features.py     ← pivots + engineers features per store/period
        |
        +------------------+
        |                  |
        v                  v
models/trainer.py    flags/rules.py    ← two parallel paths: ML models vs. rule-based flags
        |                  |
models/predictor.py        |
        |                  |
        +------------------+
        |
        v
  api/routes.py        ← Flask REST endpoints
        |
        | JSON
        v
  React Frontend (separate team)
```

---

## Layer-by-Layer Breakdown

### 1. Entry Point — `app.py`

The Flask application is created and the API blueprint is registered under the `/api` prefix. Starting the server:

```bash
python app.py
```

Flask runs on port `5000` by default (configurable via `FLASK_PORT` env var). Debug mode is off by default and is controlled by the `FLASK_DEBUG` env var.

---

### 2. Configuration — `config.py`

All environment-dependent settings live here. Nothing is hardcoded in business logic files.

| Setting | Default | Purpose |
|---|---|---|
| `ODBC_DSN` | `"MIS4400"` | ODBC data source name for SQL Server |
| `ODBC_CONNECTION_STRING` | `None` | Full connection string override (takes precedence over DSN) |
| `DB_SCHEMA` | `"Final"` | SQL Server schema name |
| `MODEL_DIR` | `"model_artifacts"` | Directory where `.joblib` model files are saved/loaded |
| `FLAG_THRESHOLDS` | See below | Dict of financial thresholds for flagging rules |

**Default flag thresholds:**

| Key | Value | Meaning |
|---|---|---|
| `gross_profit_pct_min` | `0.55` | Gross Profit must be ≥ 55% of Product Sales |
| `labor_pct_max` | `0.35` | Labor must be ≤ 35% of Product Sales |
| `profit_after_controllable_pct_min` | `0.10` | Profit After Controllable must be ≥ 10% |
| `cash_flow_pct_min` | `0.05` | Restaurant Cash Flow must be ≥ 5% |
| `yoy_sales_decline_pct` | `-0.05` | Period-over-period sales decline must not exceed -5% |

---

### 3. Database Layer — `db/`

#### `db/connection.py`
Provides a single `get_connection()` factory function. It reads `config.ODBC_CONNECTION_STRING` first; if not set, it falls back to `DSN=<config.ODBC_DSN>`. This returns a raw `pyodbc.Connection`.

#### `db/queries.py`
All SQL lives here. Each function accepts an optional `conn` argument so callers can share a connection/transaction, or pass `None` to get a fresh one. Results are returned as **pandas DataFrames** using `pd.read_sql()`.

| Function | Table | Filters |
|---|---|---|
| `get_accounts()` | `[Final].[Accounts]` | None — returns all accounts |
| `get_stores()` | `[Final].[Stores]` | None — returns all stores |
| `get_franchisees()` | `[Final].[Franchisees]` | None |
| `get_ownership()` | `[Final].[Ownership]` | None |
| `get_main_data()` | `[Final].[MainData]` | Optional: `fiscal_year`, `store_id`, `franchisee_id` |
| `get_pos_sales()` | `[Final].[POSSales]` | Optional: `fiscal_year`, `store_id` |
| `get_account_calc()` | `[Final].[AccountCalc]` | None — returns all calc rules ordered by `DestAccountID, SeqID` |

All queries use parameterized inputs (`?` placeholders) to prevent SQL injection.

---

### 4. Feature Engineering — `models/features.py`

This is the data transformation layer that converts raw, long-format account rows into a wide, ML-ready feature matrix.

**Input:**
- `main_data` — long-format DataFrame: one row per `(StoreID, FiscalYearID, CalendarID, AccountID)` with an `Amount`
- `pos_sales` — one row per `(StoreID, FiscalYearID, CalendarID)` with a `Sales` figure

**Steps:**

**Step 1 — Pivot `MainData` wide**
Each `AccountID` becomes its own column (`acct_<id>`). Values are summed per `(StoreID, FiscalYearID, CalendarID)`.

```
Before:  StoreID | CalendarID | AccountID | Amount
         101     | 01         | 10        | 50000
         101     | 01         | 60        | 28000
         101     | 01         | 110       | 15000

After:   StoreID | CalendarID | acct_10 | acct_60 | acct_110
         101     | 01         | 50000   | 28000   | 15000
```

**Step 2 — Merge POS Sales**
The `Sales` column from `POSSales` is joined onto the pivoted table on `(StoreID, FiscalYearID, CalendarID)`.

**Step 3 — Compute ratio features**
For each key P&L account, a `_pct` ratio column is computed as `acct_<id> / acct_10` (Product Sales as denominator). This normalizes values across stores of different sizes.

| Ratio Column | Formula |
|---|---|
| `acct_50_pct` | Cost of Sales / Product Sales |
| `acct_60_pct` | Gross Profit / Product Sales |
| `acct_110_pct` | Labor / Product Sales |
| `acct_230_pct` | Controllable Expenses / Product Sales |
| `acct_240_pct` | Profit After Controllable / Product Sales |
| `acct_320_pct` | Non-Controllable Expenses / Product Sales |
| `acct_440_pct` | Store Operating Income / Product Sales |
| `acct_450_pct` | Restaurant Cash Flow / Product Sales |

**Step 4 — Period-over-period change features**
Lag-1 values and absolute change columns are added for `acct_10` (Product Sales) and `Sales`, grouped within each `(StoreID, FiscalYearID)`. These give the models trend signal.

**Output:** One row per `(StoreID, FiscalYearID, CalendarID)` with all raw account amounts, ratio columns, and change columns.

---

### 5. Model Training — `models/trainer.py`

Two scikit-learn pipelines are trained and saved to disk as `.joblib` files in `model_artifacts/`.

**Run training:**
```bash
python -m models.trainer
```

Both pipelines share the same preprocessing steps:

```
SimpleImputer (median) → StandardScaler → Estimator
```

The `SimpleImputer` handles missing account values (not all stores report every account). `StandardScaler` normalizes feature magnitudes before the estimator sees them.

#### Model 1: Sales Forecaster (`sales_forecaster.joblib`)
- **Algorithm:** `RandomForestRegressor` (200 trees)
- **Target:** `Sales` (from POSSales)
- **Evaluation:** Mean Absolute Error (MAE) on an 80/20 train/test split

The model learns to predict next-period POS Sales for a store given its current-period financial feature vector.

#### Model 2: Risk Classifier (`risk_classifier.joblib`)
- **Algorithm:** `GradientBoostingClassifier` (200 estimators)
- **Target:** `is_at_risk` — a binary label (0 = healthy, 1 = at-risk) derived by running the flagging rules (`flags/rules.py`) over the training data and marking any period that triggered at least one flag as at-risk
- **Evaluation:** Classification report (precision, recall, F1) on an 80/20 split

This creates a feedback loop between the rule-based system and the ML model: the rules define the ground truth labels, and the model learns to predict risk from raw features even before rules are explicitly evaluated.

---

### 6. Financial Flagging — `flags/rules.py`

A separate, deterministic flagging system that runs threshold checks against the feature matrix. Unlike the ML models, this produces explainable, auditable results.

**Rule functions:**

| Rule | Column Checked | Threshold | Severity |
|---|---|---|---|
| `check_gross_profit` | `acct_60_pct` | < 55% | critical |
| `check_labor` | `acct_110_pct` | > 35% | warning |
| `check_profit_after_controllable` | `acct_240_pct` | < 10% | critical |
| `check_cash_flow` | `acct_450_pct` | < 5% | critical |
| `check_sales_decline` | `Sales` vs `Sales_lag1` | < -5% change | warning |

Each rule returns a list of **flag dicts** with this structure:

```json
{
  "rule":        "low_gross_profit",
  "severity":    "critical",
  "description": "Gross Profit % (48.0%) is below the minimum 55.0%",
  "value":       0.48,
  "threshold":   0.55
}
```

`compute_flags(features)` runs all rules across the full feature matrix and returns a DataFrame with:
- `StoreID`, `FiscalYearID`, `CalendarID`
- `flags` — list of triggered flag dicts for that period
- `is_at_risk` — `True` if any rule fired

---

### 7. Model Inference — `models/predictor.py`

The `Predictor` class lazy-loads both model artifacts on first use (no loading at import time). It exposes three methods:

| Method | Returns |
|---|---|
| `predict_sales(X)` | `list[float]` — predicted Sales per row |
| `predict_risk(X)` | `list[int]` — 0 (healthy) or 1 (at-risk) per row |
| `predict_risk_proba(X)` | `list[float]` — probability of at-risk (0.0–1.0) per row |

All methods drop non-numeric columns before passing data to the pipeline, matching the behavior during training.

---

### 8. REST API — `api/routes.py`

A Flask Blueprint registered at `/api`. All endpoints return JSON.

#### Reference Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Liveness check — returns `{"status": "ok"}` |
| `GET` | `/api/stores` | Full list of stores from `[Final].[Stores]` |
| `GET` | `/api/franchisees` | Full list of franchisees from `[Final].[Franchisees]` |

#### Data Endpoints (require `store_id` and `fiscal_year` query params)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/financials` | Raw P&L/BS account amounts for a store/year. Optional `calendar_id` param to filter to a single period. |
| `GET` | `/api/predictions/sales` | Sales forecast per period for the given store/year |
| `GET` | `/api/predictions/risk` | Risk label (0/1) and probability per period |
| `GET` | `/api/flags` | All triggered financial flags per period |

**Example request:**
```
GET /api/flags?store_id=101&fiscal_year=2024
```

**Example response:**
```json
{
  "flags": [
    {
      "StoreID": 101,
      "FiscalYearID": 2024,
      "CalendarID": "03",
      "is_at_risk": true,
      "flags": [
        {
          "rule": "low_gross_profit",
          "severity": "critical",
          "description": "Gross Profit % (48.0%) is below the minimum 55.0%",
          "value": 0.48,
          "threshold": 0.55
        }
      ]
    }
  ]
}
```

The internal helper `_build_features_for_request()` is shared across the prediction and flag endpoints — it parses `store_id` and `fiscal_year` from query params, queries the DB, and runs `build_feature_matrix()` before returning the feature DataFrame to the route handler.

---

## Data Flow Summary

```
Request: GET /api/predictions/sales?store_id=101&fiscal_year=2024

1. api/routes.py       — parse store_id=101, fiscal_year=2024
2. db/queries.py       — SELECT from [Final].[MainData] WHERE StoreID=101 AND FiscalYearID=2024
                       — SELECT from [Final].[POSSales] WHERE StoreID=101 AND FiscalYearID=2024
3. models/features.py  — pivot MainData wide, merge Sales, compute ratios + change cols
4. models/predictor.py — load sales_forecaster.joblib (once), run predict()
5. api/routes.py       — serialize results to JSON list
6. Frontend            — receives predicted_sales per period
```

---

## Running the Full System

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your SQL Server ODBC DSN (or set env var)
export ODBC_DSN=MIS4400
# OR
export ODBC_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;..."

# 3. Train models (one-time, or whenever data is refreshed)
python -m models.trainer

# 4. Start the API server
python app.py
# Server runs at http://localhost:5000
```

> Models must be trained before the prediction endpoints (`/api/predictions/sales`, `/api/predictions/risk`) will work. The flagging endpoint (`/api/flags`) works without trained models since it uses the rule-based system only.
