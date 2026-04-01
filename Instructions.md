# Setup Instructions

Step-by-step guide to get the MIS4400 Dashboard backend running from scratch.

---

## Prerequisites

- Python 3.10+ installed
- [Microsoft ODBC Driver 18 for SQL Server](https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server) installed on your machine
- Database credentials (ask a team member for the password)

---

## Step 1 — Clone the repository

```bash
git clone <repo-url>
cd MIS4400Dashboard
```

---

## Step 2 — Create and activate a virtual environment

```bash
python -m venv venv
```

**Windows:**
```bash
venv\Scripts\activate
```

**macOS/Linux:**
```bash
source venv/bin/activate
```

---

## Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 4 — Set the database connection string

Set the `ODBC_CONNECTION_STRING` environment variable. Replace `YOUR_PASSWORD` with the actual password.

**Windows (Command Prompt):**
```cmd
set ODBC_CONNECTION_STRING=DRIVER={ODBC Driver 18 for SQL Server};SERVER=mtu.database.windows.net;DATABASE=MTUClassProject;UID=MTU_amboop;PWD=YOUR_PASSWORD;Encrypt=Mandatory;TrustServerCertificate=Yes
```

**Windows (PowerShell):**
```powershell
$env:ODBC_CONNECTION_STRING="DRIVER={ODBC Driver 18 for SQL Server};SERVER=mtu.database.windows.net;DATABASE=MTUClassProject;UID=MTU_amboop;PWD=YOUR_PASSWORD;Encrypt=Mandatory;TrustServerCertificate=Yes"
```

**macOS/Linux (bash/zsh):**
```bash
export ODBC_CONNECTION_STRING='DRIVER={ODBC Driver 18 for SQL Server};SERVER=mtu.database.windows.net;DATABASE=MTUClassProject;UID=MTU_amboop;PWD=YOUR_PASSWORD;Encrypt=Mandatory;TrustServerCertificate=Yes'
```

> The variable must be set in the same terminal session you use to run the application. If you open a new terminal, set it again.

---

## Step 5 — Train the ML models

Run once (or whenever new data is available). Pulls data from the database and saves two model files to `model_artifacts/`.

```bash
python -m models.trainer
```

Expected output: confirmation that `sales_forecaster.joblib` and `risk_classifier.joblib` were saved.

---

## Step 6 — Choose how to run the application

### Option A — Flask API server (for the React frontend)

```bash
python app.py
```

The API will be available at `http://localhost:5000/api`. See `CLAUDE.md` for the full endpoint reference.

To run in debug mode (auto-reloads on code changes):

```bash
# macOS/Linux
FLASK_DEBUG=true python app.py

# Windows CMD
set FLASK_DEBUG=true && python app.py
```

### Option B — CLI report (no frontend needed)

Generates a financial flags and ML predictions report directly in the terminal.

```bash
# All data
python run.py

# Filter by year or store
python run.py --year 2023
python run.py --store 101
python run.py --year 2023 --store 101

# Rule-based flags only (skip ML predictions)
python run.py --flags-only

# Save results to a CSV file
python run.py --output results.csv

# Train models and run report in one step
python run.py --train
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pyodbc.InterfaceError: ('IM002', ...)` | ODBC Driver 18 is not installed — download from the link in Prerequisites |
| `Login failed for user` | Password in the connection string is wrong — check with a team member |
| `ModuleNotFoundError` | Virtual environment is not activated, or `pip install -r requirements.txt` was not run |
| `Model file not found` | Run `python -m models.trainer` (or `python run.py --train`) before starting the app |
| Environment variable not found on Windows | Use `set` in CMD or `$env:` in PowerShell — do not use `export` |
