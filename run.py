"""
Command-line runner — produces a financial report without a web frontend.

Usage
-----
# First time (or to retrain):
    python run.py --train

# After models are trained:
    python run.py
    python run.py --year 2023
    python run.py --store 101
    python run.py --year 2023 --store 101
    python run.py --output results.csv
"""

from __future__ import annotations

import argparse
import os
import sys

import pandas as pd

import config
from db.connection import get_connection
from db.queries import get_main_data, get_pos_sales, get_stores, get_franchisees, get_account_calc
from models.features import build_feature_matrix
from models.trainer import train_all, SALES_MODEL_FILE, RISK_MODEL_FILE
from flags.rules import compute_flags


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _models_exist() -> bool:
    return (
        os.path.exists(os.path.join(config.MODEL_DIR, SALES_MODEL_FILE))
        and os.path.exists(os.path.join(config.MODEL_DIR, RISK_MODEL_FILE))
    )


def _load_data(year: int | None, store_id: int | None) -> tuple[pd.DataFrame, pd.DataFrame]:
    print("Connecting to database...")
    with get_connection() as conn:
        main_data = get_main_data(fiscal_year=year, store_id=store_id, conn=conn)
        pos_sales = get_pos_sales(fiscal_year=year, store_id=store_id, conn=conn)
        stores_df = get_stores(conn=conn)
        franchisees_df = get_franchisees(conn=conn)
        account_calc = get_account_calc(conn=conn)

    # Filter out management/non-store sites (negative StoreIDs)
    main_data = main_data[main_data["StoreID"] > 0]
    pos_sales = pos_sales[pos_sales["StoreID"] > 0]

    print(f"  MainData rows:  {len(main_data):,}")
    print(f"  POSSales rows:  {len(pos_sales):,}")
    return main_data, pos_sales, stores_df, franchisees_df, account_calc


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

SEP = "-" * 90


def _print_flags_report(flags_df: pd.DataFrame, stores_df: pd.DataFrame) -> None:
    """Print a human-readable flags/risk report to stdout."""

    # Build a store name lookup
    store_names: dict[int, str] = {}
    if not stores_df.empty and "StoreID" in stores_df.columns and "StoreName" in stores_df.columns:
        store_names = dict(zip(stores_df["StoreID"], stores_df["StoreName"]))

    at_risk = flags_df[flags_df["is_at_risk"]]
    healthy = flags_df[~flags_df["is_at_risk"]]

    print()
    print("=" * 90)
    print("  FINANCIAL FLAGS REPORT")
    print("=" * 90)
    print(f"  Total periods evaluated : {len(flags_df):,}")
    print(f"  At-risk periods         : {len(at_risk):,}  ({len(at_risk)/max(len(flags_df),1):.1%})")
    print(f"  Healthy periods         : {len(healthy):,}")
    print()

    if at_risk.empty:
        print("  No flags triggered for the selected data range.")
        print()
        return

    # Summary table — one row per store/year showing flag count
    summary = (
        at_risk.groupby(["StoreID", "FiscalYearID"])
        .agg(flagged_periods=("is_at_risk", "sum"), total_flags=("flags", lambda s: sum(len(f) for f in s)))
        .reset_index()
        .sort_values("total_flags", ascending=False)
    )

    print(f"  {'StoreID':<10} {'StoreName':<30} {'FiscalYear':<12} {'Flagged Periods':>16} {'Total Flags':>12}")
    print(f"  {SEP}")
    for _, row in summary.iterrows():
        name = store_names.get(int(row["StoreID"]), "")
        print(f"  {int(row['StoreID']):<10} {name:<30} {int(row['FiscalYearID']):<12} "
              f"{int(row['flagged_periods']):>16,} {int(row['total_flags']):>12,}")
    print()

    # Detail — list each flag for each at-risk period
    print(SEP)
    print("  FLAG DETAILS")
    print(SEP)
    for _, row in at_risk.iterrows():
        store_label = f"Store {int(row['StoreID'])}"
        if int(row["StoreID"]) in store_names:
            store_label += f" — {store_names[int(row['StoreID'])]}"
        print(f"\n  {store_label}  |  Year {int(row['FiscalYearID'])}  |  Period {row['CalendarID']}")
        for flag in row["flags"]:
            sev_marker = "!!" if flag["severity"] == "critical" else " !"
            print(f"    [{sev_marker}] {flag['rule']:<35}  {flag['description']}")
    print()


def _print_sales_predictions(features: pd.DataFrame, stores_df: pd.DataFrame) -> None:
    """Print predicted sales summary."""
    from models.predictor import Predictor

    predictor = Predictor()

    store_names: dict[int, str] = {}
    if not stores_df.empty and "StoreID" in stores_df.columns and "StoreName" in stores_df.columns:
        store_names = dict(zip(stores_df["StoreID"], stores_df["StoreName"]))

    sales_preds = predictor.predict_sales(features)
    risk_labels = predictor.predict_risk(features)
    risk_probas = predictor.predict_risk_proba(features)

    pred_df = features[["StoreID", "FiscalYearID", "CalendarID"]].copy()
    pred_df["predicted_sales"] = sales_preds
    pred_df["risk_label"] = risk_labels
    pred_df["risk_probability"] = risk_probas

    # Summarise by store/year: mean predicted sales, max risk prob
    summary = (
        pred_df.groupby(["StoreID", "FiscalYearID"])
        .agg(
            avg_predicted_sales=("predicted_sales", "mean"),
            max_risk_probability=("risk_probability", "max"),
            at_risk_periods=("risk_label", "sum"),
        )
        .reset_index()
        .sort_values("max_risk_probability", ascending=False)
    )

    print(SEP)
    print("  ML PREDICTIONS SUMMARY")
    print(SEP)
    print(f"\n  {'StoreID':<10} {'StoreName':<30} {'FiscalYear':<12} "
          f"{'Avg Pred Sales':>15} {'Max Risk %':>11} {'At-Risk Periods':>16}")
    print(f"  {SEP}")
    for _, row in summary.iterrows():
        name = store_names.get(int(row["StoreID"]), "")
        risk_flag = "  <-- HIGH RISK" if row["max_risk_probability"] >= 0.6 else ""
        print(f"  {int(row['StoreID']):<10} {name:<30} {int(row['FiscalYearID']):<12} "
              f"${row['avg_predicted_sales']:>14,.2f} {row['max_risk_probability']:>10.1%} "
              f"{int(row['at_risk_periods']):>16,}{risk_flag}")
    print()

    return pred_df


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="MIS4400 Financial Dashboard — CLI Report")
    parser.add_argument("--train", action="store_true", help="Train (or retrain) ML models before reporting")
    parser.add_argument("--year", type=int, default=None, help="Filter to a specific FiscalYearID")
    parser.add_argument("--store", type=int, default=None, help="Filter to a specific StoreID")
    parser.add_argument("--output", type=str, default=None, help="Save flags results to a CSV file")
    parser.add_argument("--flags-only", action="store_true", help="Skip ML predictions, only run rule-based flags")
    args = parser.parse_args()

    # -- Train if requested or models are missing -----------------------------
    if args.train:
        print("Training models on all available data...")
        train_all()
        print()

    models_ready = _models_exist()
    if not models_ready and not args.flags_only:
        print("Warning: trained models not found. Run with --train first, or use --flags-only.")
        print(f"  Expected: {os.path.join(config.MODEL_DIR, SALES_MODEL_FILE)}")
        print()

    # -- Load data ------------------------------------------------------------
    main_data, pos_sales, stores_df, franchisees_df, account_calc = _load_data(args.year, args.store)

    if main_data.empty:
        print("No data returned for the given filters. Check your --year / --store arguments.")
        sys.exit(1)

    # -- Build features -------------------------------------------------------
    print("Building feature matrix...")
    features = build_feature_matrix(main_data, pos_sales, account_calc=account_calc)
    print(f"  Feature matrix shape: {features.shape}")

    # -- Rule-based flags -----------------------------------------------------
    print("Evaluating financial flags...")
    flags_df = compute_flags(features)
    _print_flags_report(flags_df, stores_df)

    # -- ML predictions (if models exist) -------------------------------------
    if models_ready and not args.flags_only:
        print("Running ML predictions...")
        pred_df = _print_sales_predictions(features, stores_df)
    else:
        pred_df = None

    # -- Optional CSV output --------------------------------------------------
    if args.output:
        out_df = flags_df.copy()
        out_df["flags"] = out_df["flags"].apply(
            lambda fs: "; ".join(f['rule'] for f in fs) if fs else ""
        )
        if pred_df is not None:
            out_df = out_df.merge(
                pred_df[["StoreID", "FiscalYearID", "CalendarID", "predicted_sales", "risk_label", "risk_probability"]],
                on=["StoreID", "FiscalYearID", "CalendarID"],
                how="left",
            )
        # Ensure ID columns are written as integers, not floats
        for col in ["StoreID", "FiscalYearID", "CalendarID"]:
            if col in out_df.columns:
                out_df[col] = out_df[col].astype("Int64")
        out_df.to_csv(args.output, index=False)
        print(f"Results saved to: {args.output}")

    print("Done.")


if __name__ == "__main__":
    main()
