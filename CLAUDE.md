# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MIS4400Dashboard is a class project building a **Python backend** for predictive modelling and financial flagging, integrated into another team's React web application. This repo owns the ML/data layer only — the frontend (React, CSS, HTML) is maintained by a separate team.

**Tech Stack:**
- Python 3.14
- scikit-learn (predictive modelling)
- Microsoft SQL Server (T-SQL dialect)
- REST API (to expose predictions and flags to the React frontend)

## Development Commands

```bash
# Install dependencies (once requirements.txt exists)
pip install -r requirements.txt

# Run the API server
python app.py
```

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
- `[Final].[Ownership]` — slowly-changing dimension linking franchisees to stores with `StartDate`/`EndDate` (stored as int)

**Key relationship:** `AccountCalc` drives computed metrics — when `Accounts.IsCalculated = 1`, the account's value is derived by summing `(SourceAccountID Amount × Multiplier)` rows for that `DestAccountID`, in `SeqID` order.
