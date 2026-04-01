# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIS4400Dashboard is a class project building a **Python backend** for predictive modelling and financial flagging, integrated into another team's React web application. This repo owns the ML/data layer only — the frontend (React, CSS, HTML) is maintained by a separate team.

**Tech Stack:**
- Python 3.14
- scikit-learn (predictive modelling)
- Flask (REST API)
- pyodbc (ODBC connection to SQL Server)
- Microsoft SQL Server (T-SQL dialect)

## Development Commands

### Full Flow (first-time setup)

```bash
# 1. Create and activate a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure the database connection
#    Option A — set an ODBC DSN named "MIS4400" in Windows ODBC Data Source Administrator
#    Option B — override via environment variable:
export ODBC_DSN="MIS4400"
#    Option C — full connection string override:
export ODBC_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=...;DATABASE=...;UID=...;PWD=..."

# 4. Train the ML models (requires live DB connection; writes to model_artifacts/)
python -m models.trainer

# 5. Start the Flask API server (default: http://localhost:5000)
python app.py
```

### Re-training models

```bash
# Re-run whenever new financial data is available in the DB
python -m models.trainer
# Artifacts saved to: model_artifacts/sales_forecaster.joblib
#                     model_artifacts/risk_classifier.joblib
```

### Running the API server

```bash
# Development (debug mode + auto-reload)
FLASK_DEBUG=true python app.py

# Custom port
FLASK_PORT=8080 python app.py
```

### CLI Report Runner (no frontend required)

`run.py` produces a full financial flags + ML predictions report directly in the terminal — useful for testing without starting the Flask server.

```bash
# First time (train models then report on all data)
python run.py --train

# Report on all data (models already trained)
python run.py

# Filter by year and/or store
python run.py --year 2023
python run.py --store 101
python run.py --year 2023 --store 101

# Skip ML predictions — rule-based flags only
python run.py --flags-only

# Save results to CSV
python run.py --output results.csv
```

Output sections:
- **FINANCIAL FLAGS REPORT** — per-store/period flag counts and severity details
- **ML PREDICTIONS SUMMARY** — average predicted sales, max risk probability, at-risk period count per store/year; stores with risk ≥ 60 % are marked `<-- HIGH RISK`

### API Endpoints (base: http://localhost:5000/api)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/stores` | List all stores |
| GET | `/franchisees` | List all franchisees |
| GET | `/financials?store_id=&fiscal_year=[&calendar_id=]` | Raw P&L/BS amounts |
| GET | `/predictions/sales?store_id=&fiscal_year=` | Sales forecast |
| GET | `/predictions/risk?store_id=&fiscal_year=` | At-risk score (0/1 + probability) |
| GET | `/flags?store_id=&fiscal_year=` | Rule-based financial flags |

## Repository File Descriptions

### Python Backend (created by this team)
- `app.py` — Flask application entry point; registers API blueprints and starts the server
- `config.py` — ODBC connection string and application-wide settings (DSN name, model paths, flag thresholds)
- `requirements.txt` — Python package dependencies
- `db/connection.py` — pyodbc connection factory; provides `get_connection()` for use across the app
- `db/queries.py` — SQL query functions that pull data from the `[Final]` schema (MainData, POSSales, Accounts, etc.)
- `models/features.py` — Feature engineering: pivots raw account amounts into ML-ready feature vectors; computes derived (calculated) accounts from `AccountCalc` rules since accounts like Gross Profit (60), Labor (110), Profit After Controllable (240), and Restaurant Cash Flow (450) are not stored in `MainData`; computes `acct_<id>_pct` ratio columns using Account 10 (Product Sales) as denominator; adds period-over-period lag/change columns
- `models/trainer.py` — Trains scikit-learn models (sales forecasting, financial health classification) and persists them to disk
- `models/predictor.py` — Loads trained model artifacts and runs inference for a given store/period
- `flags/rules.py` — Threshold-based financial flagging rules (e.g. low gross profit %, declining cash flow, high labor cost %) that produce structured flag objects
- `api/routes.py` — Flask Blueprint defining REST endpoints consumed by the React frontend
- `run.py` — standalone CLI runner; loads data from DB, builds feature matrix, evaluates rule-based flags, runs ML predictions, and prints a formatted report (or saves to CSV via `--output`); supports `--year`, `--store`, `--flags-only`, and `--train` flags

### SQL DDL Scripts (table definitions)
- `Accounts.sql` — DDL for `[Final].[Accounts]`: AccountID, AccountName, StatementType (PL/BS), IsCalculated flag, DivisorAccountID, DisplayOrder
- `AccountCalc.sql` — DDL for `[Final].[AccountCalc]`: DestAccountID, SeqID, SourceAccountID, Multiplier — defines multi-step derived account calculations
- `Franchisees.sql` — DDL for `[Final].[Franchisees]`: FranchiseeID, FranchiseeName, OrgID, OrgName
- `Stores.sql` — DDL for `[Final].[Stores]`: StoreID, StoreName, StoreAddress, City, StProv, Country, Status, SiteType
- `MainData.sql` — DDL for `[Final].[MainData]`: composite PK (FranchiseeID, StoreID, FiscalYearID, CalendarID, AccountID), Amount (money) — central fact table
- `Ownership.sql` — DDL for `[Final].[Ownership]`: FranchiseeID, StoreID, StartDate, EndDate (dates stored as int YYYYMMDD) — slowly-changing dimension
- `POSSales.sql` — DDL for `[Final].[POSSales]`: StoreID, FiscalYearID, CalendarID, Sales (money) — point-of-sale sales fact table

### Data Export Files (pipe-delimited `||` text exports from SQL Server)
- `Accounts.txt` — Full export of `[Final].[Accounts]`; contains P&L accounts (IDs 10–480) and Balance Sheet accounts (IDs 10010–10350)
- `AccountCalc.txt` — Full export of `[Final].[AccountCalc]`; maps derived account IDs (e.g. 50=Cost of Sales, 60=Gross Profit, 440=Store Operating Income) to their source account components with multipliers (+1 or -1)
- `MainData.txt` — Full export of `[Final].[MainData]`; ~145 MB; columns: FranchiseeID, StoreID, FiscalYearID, CalendarID, AccountID, Amount — central fact table containing all financial account amounts per store/period
- `Ownership.txt` — Full export of `[Final].[Ownership]` joined with franchisee/store names; ~647 KB; columns: OrgID, OrgName, FranID, FranchiseeName, StoreID, StoreName, StartDate, EndDate
- `POSSales.txt` — Full export of `[Final].[POSSales]`; ~2.5 MB; columns: StoreID, FiscalYearId, CalendarID, Sales
- `Stores[1].txt` — Full export of `[Final].[Stores]`; ~621 KB; columns: StoreID, StoreName, StoreAddress, City, StProv, Country, Status, SiteType

## Database Architecture

All tables live in the `[Final]` schema on SQL Server. The schema follows a **star schema** pattern for financial reporting:

**Dimension tables:**
- `[Final].[Accounts]` — financial accounts with `StatementType`, `IsCalculated` flag, and optional `DivisorAccountID` for ratio calculations
- `[Final].[Franchisees]` — franchisee organizations (`FranchiseeID`, `OrgID`/`OrgName`)
- `[Final].[Stores]` — store locations with address, status, and site type

**Fact tables:**
- `[Final].[MainData]` — central fact table; composite PK of `(FranchiseeID, StoreID, FiscalYearID, CalendarID, AccountID)` with `Amount (money)`
- `[Final].[POSSales]` — point-of-sale sales data keyed by `(StoreID, FiscalYearID, CalendarID)`

**Configuration/bridge tables:**
- `[Final].[AccountCalc]` — defines how calculated accounts are derived from source accounts via `SourceAccountID` and `Multiplier`; supports multi-step calculations via `SeqID`
- `[Final].[Ownership]` — slowly-changing dimension linking franchisees to stores with `StartDate`/`EndDate` (stored as int YYYYMMDD)

**Key relationship:** `AccountCalc` drives computed metrics — when `Accounts.IsCalculated = 1`, the account's value is derived by summing `(SourceAccountID Amount × Multiplier)` rows for that `DestAccountID`, in `SeqID` order.

**Key account IDs (P&L):**
- `10` = Product Sales (revenue denominator for ratios)
- `60` = Gross Profit
- `110` = Labor
- `240` = Profit After Controllable
- `440` = Store Operating Income
- `450` = Restaurant Cash Flow

**CalendarID** is a 2-digit period (e.g. `01`–`13`) representing fiscal periods within a year.
