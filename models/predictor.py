"""
Model inference.

Loads trained model artifacts from disk and runs predictions for a given
store or set of feature rows.

Usage
-----
    from models.predictor import Predictor
    p = Predictor()
    sales_pred = p.predict_sales(feature_row)
    risk_pred  = p.predict_risk(feature_row)
"""

from __future__ import annotations

import os
import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

import config
from models.trainer import SALES_MODEL_FILE, RISK_MODEL_FILE


class Predictor:
    """Lazy-loading wrapper around both trained model pipelines."""

    def __init__(self) -> None:
        self._sales_model: Pipeline | None = None
        self._risk_model: Pipeline | None = None

    # ------------------------------------------------------------------ load

    def _load_sales_model(self) -> Pipeline:
        if self._sales_model is None:
            path = os.path.join(config.MODEL_DIR, SALES_MODEL_FILE)
            self._sales_model = joblib.load(path)
        return self._sales_model

    def _load_risk_model(self) -> Pipeline:
        if self._risk_model is None:
            path = os.path.join(config.MODEL_DIR, RISK_MODEL_FILE)
            self._risk_model = joblib.load(path)
        return self._risk_model

    # --------------------------------------------------------------- predict

    def predict_sales(self, X: pd.DataFrame) -> list[float]:
        """
        Predict next-period Sales for each row in X.

        Parameters
        ----------
        X : DataFrame
            Feature rows produced by models.features.build_feature_matrix().
            Non-numeric columns are dropped automatically.

        Returns
        -------
        List of predicted Sales amounts (one per input row).
        """
        model = self._load_sales_model()
        X_num = X.select_dtypes(include="number")
        return model.predict(X_num).tolist()

    def predict_risk(self, X: pd.DataFrame) -> list[int]:
        """
        Predict financial risk label (0 = healthy, 1 = at-risk) for each row.

        Parameters
        ----------
        X : DataFrame
            Feature rows produced by models.features.build_feature_matrix().

        Returns
        -------
        List of integer labels (0 or 1).
        """
        model = self._load_risk_model()
        X_num = X.select_dtypes(include="number")
        return model.predict(X_num).tolist()

    def predict_risk_proba(self, X: pd.DataFrame) -> list[float]:
        """Return probability of at-risk (class 1) for each row."""
        model = self._load_risk_model()
        X_num = X.select_dtypes(include="number")
        return model.predict_proba(X_num)[:, 1].tolist()
