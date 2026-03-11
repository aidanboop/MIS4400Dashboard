"""
Feature engineering for predictive models.

Transforms raw MainData + POSSales rows into a flat feature matrix where
each row represents one (StoreID, FiscalYearID, CalendarID) observation.

Key steps
---------
1. Pivot MainData so each AccountID becomes its own column.
2. Attach POSSales.Sales as the primary revenue figure.
3. Compute % ratios for the key P&L lines (using AccountID 10 — Product Sales
   — as the denominator, consistent with DivisorAccountID in Accounts).
4. Add period-over-period change features for trend detection.
"""

from __future__ import annotations

import pandas as pd

# Key account IDs from [Final].[Accounts] (P&L, StatementType='PL')
ACCT_PRODUCT_SALES = 10
ACCT_COST_OF_SALES = 50
ACCT_GROSS_PROFIT = 60
ACCT_LABOR = 110
ACCT_CONTROLLABLE_EXPENSES = 230
ACCT_PROFIT_AFTER_CONTROLLABLE = 240
ACCT_NON_CONTROLLABLE_EXPENSES = 320
ACCT_STORE_OPERATING_INCOME = 440
ACCT_RESTAURANT_CASH_FLOW = 450


def build_feature_matrix(
    main_data: pd.DataFrame,
    pos_sales: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a per-period feature matrix from raw query results.

    Parameters
    ----------
    main_data : DataFrame
        Result of db.queries.get_main_data() — columns:
        FranchiseeID, StoreID, FiscalYearID, CalendarID, AccountID, Amount
    pos_sales : DataFrame
        Result of db.queries.get_pos_sales() — columns:
        StoreID, FiscalYearID, CalendarID, Sales

    Returns
    -------
    DataFrame with one row per (StoreID, FiscalYearID, CalendarID) and
    engineered feature columns.
    """
    # -- 1. Pivot account amounts wide ----------------------------------------
    pivot = main_data.pivot_table(
        index=["StoreID", "FiscalYearID", "CalendarID"],
        columns="AccountID",
        values="Amount",
        aggfunc="sum",
    ).reset_index()
    # Rename AccountID columns to acct_<id> to avoid integer column names
    pivot.columns = [
        f"acct_{c}" if isinstance(c, int) else c for c in pivot.columns
    ]

    # -- 2. Merge POS Sales ---------------------------------------------------
    features = pivot.merge(pos_sales, on=["StoreID", "FiscalYearID", "CalendarID"], how="left")

    # -- 3. Ratio features (pct of Product Sales) ----------------------------
    rev_col = f"acct_{ACCT_PRODUCT_SALES}"
    if rev_col in features.columns:
        for acct_id in [
            ACCT_COST_OF_SALES,
            ACCT_GROSS_PROFIT,
            ACCT_LABOR,
            ACCT_CONTROLLABLE_EXPENSES,
            ACCT_PROFIT_AFTER_CONTROLLABLE,
            ACCT_NON_CONTROLLABLE_EXPENSES,
            ACCT_STORE_OPERATING_INCOME,
            ACCT_RESTAURANT_CASH_FLOW,
        ]:
            col = f"acct_{acct_id}"
            if col in features.columns:
                features[f"{col}_pct"] = features[col] / features[rev_col].replace(0, float("nan"))

    # -- 4. Period-over-period change (within same FiscalYear) ---------------
    features = features.sort_values(["StoreID", "FiscalYearID", "CalendarID"])
    for col in [rev_col, "Sales"]:
        if col in features.columns:
            features[f"{col}_lag1"] = features.groupby(["StoreID", "FiscalYearID"])[col].shift(1)
            features[f"{col}_chg"] = features[col] - features[f"{col}_lag1"]

    return features.reset_index(drop=True)


def get_training_target(features: pd.DataFrame, target_col: str = "Sales") -> tuple[pd.DataFrame, pd.Series]:
    """
    Split feature matrix into X (features) and y (target series).

    Parameters
    ----------
    features : DataFrame
        Output of build_feature_matrix().
    target_col : str
        Column to use as the prediction target.

    Returns
    -------
    (X, y) tuple
    """
    id_cols = ["StoreID", "FiscalYearID", "CalendarID"]
    drop_cols = id_cols + [target_col]
    X = features.drop(columns=[c for c in drop_cols if c in features.columns])
    y = features[target_col]
    return X, y
