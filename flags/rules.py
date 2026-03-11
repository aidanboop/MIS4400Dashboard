"""
Threshold-based financial flagging rules.

Each rule inspects a feature row (output of models.features.build_feature_matrix)
and returns a structured flag dict when a threshold is breached.

compute_flags() runs all rules across a DataFrame and returns a summary
DataFrame with one row per (StoreID, FiscalYearID, CalendarID) plus:
  - a list of triggered flag dicts
  - an is_at_risk boolean (True if any rule fired)

Flag dict schema
----------------
{
    "rule":        str   — rule identifier, e.g. "low_gross_profit"
    "severity":    str   — "warning" | "critical"
    "description": str   — human-readable explanation
    "value":       float — the actual metric value that triggered the flag
    "threshold":   float — the threshold it was compared against
}
"""

from __future__ import annotations

import pandas as pd
import config

T = config.FLAG_THRESHOLDS  # shorthand


# ---------------------------------------------------------------------------
# Individual rule functions
# ---------------------------------------------------------------------------

def _flag(rule: str, severity: str, description: str, value: float, threshold: float) -> dict:
    return {
        "rule": rule,
        "severity": severity,
        "description": description,
        "value": round(float(value), 4),
        "threshold": round(float(threshold), 4),
    }


def check_gross_profit(row: pd.Series) -> list[dict]:
    """Flag if Gross Profit % is below minimum."""
    col = "acct_60_pct"
    flags: list[dict] = []
    if col in row and pd.notna(row[col]):
        threshold = T["gross_profit_pct_min"]
        if row[col] < threshold:
            flags.append(_flag(
                rule="low_gross_profit",
                severity="critical",
                description=f"Gross Profit % ({row[col]:.1%}) is below the minimum {threshold:.1%}",
                value=row[col],
                threshold=threshold,
            ))
    return flags


def check_labor(row: pd.Series) -> list[dict]:
    """Flag if Labor % exceeds maximum."""
    col = "acct_110_pct"
    flags: list[dict] = []
    if col in row and pd.notna(row[col]):
        threshold = T["labor_pct_max"]
        if row[col] > threshold:
            flags.append(_flag(
                rule="high_labor_cost",
                severity="warning",
                description=f"Labor % ({row[col]:.1%}) exceeds the maximum {threshold:.1%}",
                value=row[col],
                threshold=threshold,
            ))
    return flags


def check_profit_after_controllable(row: pd.Series) -> list[dict]:
    """Flag if Profit After Controllable % is below minimum."""
    col = "acct_240_pct"
    flags: list[dict] = []
    if col in row and pd.notna(row[col]):
        threshold = T["profit_after_controllable_pct_min"]
        if row[col] < threshold:
            flags.append(_flag(
                rule="low_controllable_profit",
                severity="critical",
                description=f"Profit After Controllable % ({row[col]:.1%}) is below the minimum {threshold:.1%}",
                value=row[col],
                threshold=threshold,
            ))
    return flags


def check_cash_flow(row: pd.Series) -> list[dict]:
    """Flag if Restaurant Cash Flow % is below minimum."""
    col = "acct_450_pct"
    flags: list[dict] = []
    if col in row and pd.notna(row[col]):
        threshold = T["cash_flow_pct_min"]
        if row[col] < threshold:
            flags.append(_flag(
                rule="low_cash_flow",
                severity="critical",
                description=f"Restaurant Cash Flow % ({row[col]:.1%}) is below the minimum {threshold:.1%}",
                value=row[col],
                threshold=threshold,
            ))
    return flags


def check_sales_decline(row: pd.Series) -> list[dict]:
    """Flag if period-over-period Sales change % is below threshold."""
    flags: list[dict] = []
    if "Sales" in row and "Sales_lag1" in row:
        if pd.notna(row["Sales"]) and pd.notna(row["Sales_lag1"]) and row["Sales_lag1"] != 0:
            chg_pct = (row["Sales"] - row["Sales_lag1"]) / abs(row["Sales_lag1"])
            threshold = T["yoy_sales_decline_pct"]
            if chg_pct < threshold:
                flags.append(_flag(
                    rule="sales_decline",
                    severity="warning",
                    description=f"Sales declined {chg_pct:.1%} period-over-period (threshold {threshold:.1%})",
                    value=chg_pct,
                    threshold=threshold,
                ))
    return flags


# Registry of all rule functions
_RULES = [
    check_gross_profit,
    check_labor,
    check_profit_after_controllable,
    check_cash_flow,
    check_sales_decline,
]


# ---------------------------------------------------------------------------
# Bulk evaluation
# ---------------------------------------------------------------------------

def evaluate_row(row: pd.Series) -> list[dict]:
    """Run all rules against a single feature row and return triggered flags."""
    triggered: list[dict] = []
    for rule_fn in _RULES:
        triggered.extend(rule_fn(row))
    return triggered


def compute_flags(features: pd.DataFrame) -> pd.DataFrame:
    """
    Run all flagging rules across an entire feature matrix.

    Parameters
    ----------
    features : DataFrame
        Output of models.features.build_feature_matrix().

    Returns
    -------
    DataFrame with columns:
        StoreID, FiscalYearID, CalendarID, flags, is_at_risk
    """
    id_cols = ["StoreID", "FiscalYearID", "CalendarID"]
    results = []

    for _, row in features.iterrows():
        triggered = evaluate_row(row)
        results.append({
            "StoreID": row.get("StoreID"),
            "FiscalYearID": row.get("FiscalYearID"),
            "CalendarID": row.get("CalendarID"),
            "flags": triggered,
            "is_at_risk": len(triggered) > 0,
        })

    return pd.DataFrame(results)
