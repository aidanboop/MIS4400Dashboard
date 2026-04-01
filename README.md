# MIS4400Dashboard

A Python backend for predictive modelling and financial flagging, built as part of the MIS4400 class project. This repository owns the ML/data layer and exposes a REST API consumed by a separate team's React frontend.

---

## Tech Stack

- **Python 3.14**
- **Flask** — REST API server
- **scikit-learn** — predictive modelling (sales forecasting, financial health classification)
- **pyodbc** — ODBC connection to Microsoft SQL Server
- **Microsoft SQL Server** — data store (T-SQL dialect, `[Final]` schema)

---

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run the API server
python app.py
```

---

## Repository Structure

```
MIS4400Dashboard/
│
├── app.py                  # Flask entry point; registers blueprints and starts server
├── config.py               # ODBC connection string, DSN name, model paths, flag thresholds
├── requirements.txt        # Python package dependencies
│
├── api/
│   ├── __init__.py
│   └── routes.py           # Flask Blueprint; REST endpoints consumed by the React frontend
│
├── db/
│   ├── __init__.py
│   ├── connection.py       # pyodbc connection factory (get_connection())
│   └── queries.py          # SQL query functions pulling from [Final] schema tables
│
├── models/
│   ├── __init__.py
│   ├── features.py         # Feature engineering: pivots raw account amounts into ML-ready vectors,
│   │                       #   computes ratios via DivisorAccountID, handles AccountCalc derived metrics
│   ├── trainer.py          # Trains scikit-learn models and persists artifacts to disk
│   └── predictor.py        # Loads trained model artifacts and runs inference per store/period
│
├── flags/
│   ├── __init__.py
│   └── rules.py            # Threshold-based financial flagging rules (e.g. low gross profit %,
│                           #   declining cash flow, high labor cost %); produces structured flag objects
│
├── SQL DDL Scripts/
│   ├── Accounts.sql        # [Final].[Accounts]: AccountID, AccountName, StatementType, IsCalculated,
│   │                       #   DivisorAccountID, DisplayOrder
│   ├── AccountCalc.sql     # [Final].[AccountCalc]: DestAccountID, SeqID, SourceAccountID, Multiplier
│   ├── Franchisees.sql     # [Final].[Franchisees]: FranchiseeID, FranchiseeName, OrgID, OrgName
│   ├── MainData.sql        # [Final].[MainData]: composite PK (FranchiseeID, StoreID, FiscalYearID,
│   │                       #   CalendarID, AccountID), Amount (money) — central fact table
│   ├── Ownership.sql       # [Final].[Ownership]: FranchiseeID, StoreID, StartDate, EndDate (int YYYYMMDD)
│   ├── POSSales.sql        # [Final].[POSSales]: StoreID, FiscalYearID, CalendarID, Sales (money)
│   └── Stores.sql          # [Final].[Stores]: StoreID, StoreName, StoreAddress, City, StProv,
│                           #   Country, Status, SiteType
│
└── Data Export Files/      # Pipe-delimited (||) exports from SQL Server for local development
    ├── Accounts.txt        # P&L accounts (IDs 10–480) and Balance Sheet accounts (IDs 10010–10350)
    ├── AccountCalc.txt     # Derived account mappings (e.g. ID 60=Gross Profit, 440=Store Operating Income)
    ├── MainData.txt        # ~145 MB central fact table; all financial amounts per store/period
    ├── Ownership.txt       # ~647 KB; franchisee-to-store ownership with start/end dates
    ├── POSSales.txt        # ~2.5 MB; point-of-sale sales by store and fiscal period
    └── Stores[1].txt       # ~621 KB; full store location and status data
```

---

## Database Architecture

All tables live in the `[Final]` schema on SQL Server, following a **star schema** pattern:

### Dimension Tables
| Table | Key Columns |
|---|---|
| `[Final].[Accounts]` | `AccountID`, `AccountName`, `StatementType` (PL/BS), `IsCalculated`, `DivisorAccountID` |
| `[Final].[Franchisees]` | `FranchiseeID`, `FranchiseeName`, `OrgID`, `OrgName` |
| `[Final].[Stores]` | `StoreID`, `StoreName`, `City`, `StProv`, `Country`, `Status`, `SiteType` |

### Fact Tables
| Table | Key Columns |
|---|---|
| `[Final].[MainData]` | `FranchiseeID`, `StoreID`, `FiscalYearID`, `CalendarID`, `AccountID`, `Amount` |
| `[Final].[POSSales]` | `StoreID`, `FiscalYearID`, `CalendarID`, `Sales` |

### Configuration / Bridge Tables
| Table | Purpose |
|---|---|
| `[Final].[AccountCalc]` | Defines how calculated accounts are derived from source accounts via `SourceAccountID × Multiplier` |
| `[Final].[Ownership]` | Slowly-changing dimension linking franchisees to stores with date ranges (int YYYYMMDD) |

### Key Account IDs (P&L)
| ID | Description |
|---|---|
| `10` | Product Sales (revenue denominator for ratios) |
| `60` | Gross Profit |
| `110` | Labor |
| `240` | Profit After Controllable |
| `440` | Store Operating Income |
| `450` | Restaurant Cash Flow |

> **CalendarID** is a 2-digit fiscal period (e.g. `01`–`13`) within a fiscal year.

> **AccountCalc logic:** When `Accounts.IsCalculated = 1`, the account's value is derived by summing `SourceAccountID Amount × Multiplier` for that `DestAccountID`, applied in `SeqID` order.

---

## Backend System Overview

### Predictive Modelling
The `models/` package handles two ML tasks:

- **Sales Forecasting** — predicts future period sales for a given store using historical `MainData` and `POSSales` records as time-series input features.
- **Financial Health Classification** — classifies a store's financial health (e.g. healthy / at-risk / distressed) based on engineered ratios derived from P&L accounts such as gross profit margin, labor cost %, and cash flow trend.

Feature engineering (`features.py`) pivots raw account-level rows into wide feature vectors per store/period, derives calculated accounts (Gross Profit, Labor, etc.) from `AccountCalc` rules — since these are not stored in `MainData` — and computes ratio metrics using Account 10 (Product Sales) as the denominator. Trained model artifacts are persisted to disk by `trainer.py` and loaded at inference time by `predictor.py`.

### Financial Flagging
The `flags/rules.py` module applies threshold-based rules against computed financial metrics to surface actionable warnings. Example flags include:

- Gross profit % below threshold
- Declining cash flow over consecutive periods
- Labor cost % exceeding acceptable range
- Store Operating Income outside expected bounds

Each rule produces a structured flag object (store ID, flag type, severity, value, threshold) that the API returns to the frontend for display.

### REST API
`api/routes.py` exposes Flask endpoints that the React frontend calls to retrieve predictions, flags, and financial summaries for a given store and fiscal period.

---

## Notes

- The frontend (React, CSS, HTML) is maintained by a separate team and is not part of this repository.
- `MainData.txt` is tracked via Git LFS due to its ~145 MB size.
