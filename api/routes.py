"""
REST API routes consumed by the React frontend.

All endpoints return JSON.  Register this blueprint in app.py with
url_prefix="/api".

Endpoints
---------
GET  /api/health                         — liveness check
GET  /api/stores                         — list all stores
GET  /api/franchisees                    — list all franchisees
GET  /api/predictions/sales              — sales forecast for a store/period
GET  /api/predictions/risk               — at-risk score for a store/period
GET  /api/flags                          — financial flags for a store/period
GET  /api/financials                     — raw P&L/BS data for a store/period
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from db.queries import (
    get_stores,
    get_franchisees,
    get_main_data,
    get_pos_sales,
    get_account_calc,
)
from models.features import build_feature_matrix
from models.predictor import Predictor
from flags.rules import compute_flags

bp = Blueprint("api", __name__)
_predictor = Predictor()  # lazy-loads models on first prediction call


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@bp.get("/health")
def health():
    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

@bp.get("/stores")
def stores():
    df = get_stores()
    return jsonify(df.to_dict(orient="records"))


@bp.get("/franchisees")
def franchisees():
    df = get_franchisees()
    return jsonify(df.to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Helper: build features for a single store/year query
# ---------------------------------------------------------------------------

def _build_features_for_request():
    """
    Parse common query params (store_id, fiscal_year) and return a feature
    DataFrame.  Returns (features_df, error_response) — one will be None.
    """
    store_id = request.args.get("store_id", type=int)
    fiscal_year = request.args.get("fiscal_year", type=int)

    if store_id is None or fiscal_year is None:
        return None, (jsonify({"error": "store_id and fiscal_year are required"}), 400)

    main_data = get_main_data(store_id=store_id, fiscal_year=fiscal_year)
    pos_sales = get_pos_sales(store_id=store_id, fiscal_year=fiscal_year)

    if main_data.empty:
        return None, (jsonify({"error": "No data found for the given store/year"}), 404)

    account_calc = get_account_calc()
    features = build_feature_matrix(main_data, pos_sales, account_calc=account_calc)
    return features, None


# ---------------------------------------------------------------------------
# Financials (raw account amounts)
# ---------------------------------------------------------------------------

@bp.get("/financials")
def financials():
    """
    Return raw MainData amounts for a store/year, optionally filtered by
    calendar period.

    Query params: store_id, fiscal_year, [calendar_id]
    """
    store_id = request.args.get("store_id", type=int)
    fiscal_year = request.args.get("fiscal_year", type=int)
    calendar_id = request.args.get("calendar_id", type=str)

    if store_id is None or fiscal_year is None:
        return jsonify({"error": "store_id and fiscal_year are required"}), 400

    df = get_main_data(store_id=store_id, fiscal_year=fiscal_year)
    if calendar_id is not None:
        df = df[df["CalendarID"].astype(str) == calendar_id]

    return jsonify(df.to_dict(orient="records"))


# ---------------------------------------------------------------------------
# Predictions
# ---------------------------------------------------------------------------

@bp.get("/predictions/sales")
def predict_sales():
    """
    Return predicted next-period Sales for a store/year.

    Query params: store_id, fiscal_year
    Response: { "predictions": [{ "StoreID":…, "FiscalYearID":…, "CalendarID":…, "predicted_sales":… }] }
    """
    features, err = _build_features_for_request()
    if err:
        return err

    preds = _predictor.predict_sales(features)
    results = []
    for i, row in features.iterrows():
        results.append({
            "StoreID": int(row["StoreID"]),
            "FiscalYearID": int(row["FiscalYearID"]),
            "CalendarID": row["CalendarID"],
            "predicted_sales": round(preds[i], 2),
        })

    return jsonify({"predictions": results})


@bp.get("/predictions/risk")
def predict_risk():
    """
    Return financial risk score for each period of a store/year.

    Query params: store_id, fiscal_year
    Response: { "predictions": [{ …, "risk_label": 0|1, "risk_probability": 0.0–1.0 }] }
    """
    features, err = _build_features_for_request()
    if err:
        return err

    labels = _predictor.predict_risk(features)
    probas = _predictor.predict_risk_proba(features)
    results = []
    for i, row in features.iterrows():
        results.append({
            "StoreID": int(row["StoreID"]),
            "FiscalYearID": int(row["FiscalYearID"]),
            "CalendarID": row["CalendarID"],
            "risk_label": labels[i],
            "risk_probability": round(probas[i], 4),
        })

    return jsonify({"predictions": results})


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------

@bp.get("/flags")
def flags():
    """
    Return rule-based financial flags for a store/year.

    Query params: store_id, fiscal_year
    Response: { "flags": [{ …, "is_at_risk": bool, "flags": [ flag_dict, … ] }] }
    """
    features, err = _build_features_for_request()
    if err:
        return err

    flags_df = compute_flags(features)
    return jsonify({"flags": flags_df.to_dict(orient="records")})
