"""
Application-wide configuration.

Set ODBC_DSN (or the individual DSN components) to match your SQL Server
ODBC data source.  All other values have sensible defaults.
"""

import os

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

# Name of the ODBC DSN configured on this machine, OR a full connection string.
# Example DSN:  "MIS4400"
# Example full: "DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=..."
ODBC_DSN: str = os.getenv("ODBC_DSN", "MIS4400")

# Full connection string override (takes precedence over ODBC_DSN when set)
ODBC_CONNECTION_STRING: str | None = os.getenv("ODBC_CONNECTION_STRING", None)

DB_SCHEMA: str = "Final"

# ---------------------------------------------------------------------------
# Model artifacts
# ---------------------------------------------------------------------------

# Directory where trained model files (.joblib) are stored/loaded
MODEL_DIR: str = os.getenv("MODEL_DIR", "model_artifacts")

# ---------------------------------------------------------------------------
# Financial flag thresholds  (expressed as decimals, e.g. 0.30 = 30%)
# ---------------------------------------------------------------------------

FLAG_THRESHOLDS: dict = {
    # Gross Profit % below this → flag as low margin
    "gross_profit_pct_min": 0.55,
    # Labor % above this → flag as high labor
    "labor_pct_max": 0.35,
    # Profit After Controllable % below this → flag as low controllable profit
    "profit_after_controllable_pct_min": 0.10,
    # Restaurant Cash Flow % below this → flag as negative cash flow risk
    "cash_flow_pct_min": 0.05,
    # Year-over-year sales decline threshold (negative means decline)
    "yoy_sales_decline_pct": -0.05,
}

# ---------------------------------------------------------------------------
# Flask
# ---------------------------------------------------------------------------

FLASK_DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
FLASK_PORT: int = int(os.getenv("FLASK_PORT", "5000"))
