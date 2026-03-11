"""
Model training.

Trains two scikit-learn models and persists them to disk via joblib:
  1. sales_forecaster  — RandomForestRegressor to predict next-period Sales
  2. risk_classifier   — GradientBoostingClassifier to flag financially at-risk stores

Usage
-----
    python -m models.trainer          # trains on all available data
"""

from __future__ import annotations

import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, classification_report

import config
from db.connection import get_connection
from db.queries import get_main_data, get_pos_sales
from models.features import build_feature_matrix, get_training_target
from flags.rules import compute_flags

# Artifact filenames
SALES_MODEL_FILE = "sales_forecaster.joblib"
RISK_MODEL_FILE = "risk_classifier.joblib"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_numeric_pipeline(estimator) -> Pipeline:
    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", estimator),
    ])


def _ensure_model_dir() -> str:
    os.makedirs(config.MODEL_DIR, exist_ok=True)
    return config.MODEL_DIR


# ---------------------------------------------------------------------------
# Training routines
# ---------------------------------------------------------------------------

def train_sales_forecaster(features: pd.DataFrame) -> Pipeline:
    """Train a RandomForestRegressor to predict Sales."""
    X, y = get_training_target(features, target_col="Sales")
    X = X.select_dtypes(include="number")  # drop any remaining non-numeric

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = _make_numeric_pipeline(
        RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)
    )
    model.fit(X_train, y_train)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"[sales_forecaster] MAE on hold-out: ${mae:,.2f}")

    return model


def train_risk_classifier(features: pd.DataFrame) -> Pipeline:
    """
    Train a GradientBoostingClassifier to predict at-risk stores.

    The label is derived from the financial flagging rules: a store-period is
    labeled 1 (at-risk) if it triggers any critical flag, else 0.
    """
    flags_df = compute_flags(features)
    y = flags_df["is_at_risk"].astype(int)

    X, _ = get_training_target(features, target_col="Sales")
    X = X.select_dtypes(include="number")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = _make_numeric_pipeline(
        GradientBoostingClassifier(n_estimators=200, random_state=42)
    )
    model.fit(X_train, y_train)

    print("[risk_classifier] Classification report on hold-out:")
    print(classification_report(y_test, model.predict(X_test)))

    return model


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def train_all() -> None:
    """Pull data from SQL Server, build features, train and save both models."""
    print("Connecting to database...")
    with get_connection() as conn:
        main_data = get_main_data(conn=conn)
        pos_sales = get_pos_sales(conn=conn)

    print(f"Loaded {len(main_data):,} MainData rows and {len(pos_sales):,} POSSales rows.")
    features = build_feature_matrix(main_data, pos_sales)
    print(f"Feature matrix: {features.shape}")

    model_dir = _ensure_model_dir()

    sales_model = train_sales_forecaster(features)
    joblib.dump(sales_model, os.path.join(model_dir, SALES_MODEL_FILE))
    print(f"Saved → {os.path.join(model_dir, SALES_MODEL_FILE)}")

    risk_model = train_risk_classifier(features)
    joblib.dump(risk_model, os.path.join(model_dir, RISK_MODEL_FILE))
    print(f"Saved → {os.path.join(model_dir, RISK_MODEL_FILE)}")


if __name__ == "__main__":
    train_all()
