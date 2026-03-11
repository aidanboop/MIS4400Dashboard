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

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python app.py
```

## Repository File Descriptions

### Python Backend (created by this team)
- `app.py` — Flask application entry point; registers API blueprints and starts the server
- `config.py` — ODBC connection string and application-wide settings (DSN name, model paths, flag thresholds)
- `requirements.txt` — Python package dependencies
- `db/connection.py` — pyodbc connection factory; provides `get_connection()` for use across the app
- `db/queries.py` — SQL query functions that pull data from the `[Final]` schema (MainData, POSSales, Accounts, etc.)
- `models/features.py` — Feature engineering: pivots raw account amounts into ML-ready feature vectors, computes ratios using `DivisorAccountID`, handles `AccountCalc` derived metrics
- `models/trainer.py` — Trains scikit-learn models (sales forecasting, financial health classification) and persists them to disk
- `models/predictor.py` — Loads trained model artifacts and runs inference for a given store/period
- `flags/rules.py` — Threshold-based financial flagging rules (e.g. low gross profit %, declining cash flow, high labor cost %) that produce structured flag objects
- `api/routes.py` — Flask Blueprint defining REST endpoints consumed by the React frontend

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
