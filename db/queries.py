"""
SQL query helpers.

All functions accept an optional pyodbc connection so callers can share a
transaction, or pass None to open a fresh connection per call.
"""

from __future__ import annotations

import pandas as pd
import pyodbc

from db.connection import get_connection
import config

S = config.DB_SCHEMA  # shorthand: "Final"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _conn(conn: pyodbc.Connection | None) -> tuple[pyodbc.Connection, bool]:
    """Return (connection, owned) where owned=True means we opened it."""
    if conn is None:
        return get_connection(), True
    return conn, False


# ---------------------------------------------------------------------------
# Dimension lookups
# ---------------------------------------------------------------------------

def get_accounts(conn: pyodbc.Connection | None = None) -> pd.DataFrame:
    """
    Returns all rows from [Final].[Accounts].
    Columns: AccountID, AccountName, StatementType, IsCalculated,
             DivisorAccountID, DisplayOrder
    """
    c, owned = _conn(conn)
    try:
        sql = f"SELECT * FROM [{S}].[Accounts] ORDER BY DisplayOrder"
        return pd.read_sql(sql, c)
    finally:
        if owned:
            c.close()


def get_stores(conn: pyodbc.Connection | None = None) -> pd.DataFrame:
    """
    Returns all rows from [Final].[Stores].
    Columns: StoreID, StoreName, StoreAddress, City, StProv, Country, Status, SiteType
    """
    c, owned = _conn(conn)
    try:
        sql = f"SELECT * FROM [{S}].[Stores]"
        return pd.read_sql(sql, c)
    finally:
        if owned:
            c.close()


def get_franchisees(conn: pyodbc.Connection | None = None) -> pd.DataFrame:
    """
    Returns all rows from [Final].[Franchisees].
    Columns: FranchiseeID, FranchiseeName, OrgID, OrgName
    """
    c, owned = _conn(conn)
    try:
        sql = f"SELECT * FROM [{S}].[Franchisees]"
        return pd.read_sql(sql, c)
    finally:
        if owned:
            c.close()


def get_ownership(conn: pyodbc.Connection | None = None) -> pd.DataFrame:
    """
    Returns all rows from [Final].[Ownership].
    Columns: FranchiseeID, StoreID, StartDate, EndDate
    Note: dates are stored as int (YYYYMMDD).
    """
    c, owned = _conn(conn)
    try:
        sql = f"SELECT * FROM [{S}].[Ownership]"
        return pd.read_sql(sql, c)
    finally:
        if owned:
            c.close()


# ---------------------------------------------------------------------------
# Fact data
# ---------------------------------------------------------------------------

def get_main_data(
    fiscal_year: int | None = None,
    store_id: int | None = None,
    franchisee_id: int | None = None,
    conn: pyodbc.Connection | None = None,
) -> pd.DataFrame:
    """
    Returns rows from [Final].[MainData] with optional filters.
    Columns: FranchiseeID, StoreID, FiscalYearID, CalendarID, AccountID, Amount
    """
    c, owned = _conn(conn)
    try:
        conditions = []
        params: list = []
        if fiscal_year is not None:
            conditions.append("FiscalYearID = ?")
            params.append(fiscal_year)
        if store_id is not None:
            conditions.append("StoreID = ?")
            params.append(store_id)
        if franchisee_id is not None:
            conditions.append("FranchiseeID = ?")
            params.append(franchisee_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM [{S}].[MainData] {where}"
        return pd.read_sql(sql, c, params=params)
    finally:
        if owned:
            c.close()


def get_pos_sales(
    fiscal_year: int | None = None,
    store_id: int | None = None,
    conn: pyodbc.Connection | None = None,
) -> pd.DataFrame:
    """
    Returns rows from [Final].[POSSales] with optional filters.
    Columns: StoreID, FiscalYearID, CalendarID, Sales
    """
    c, owned = _conn(conn)
    try:
        conditions = []
        params: list = []
        if fiscal_year is not None:
            conditions.append("FiscalYearID = ?")
            params.append(fiscal_year)
        if store_id is not None:
            conditions.append("StoreID = ?")
            params.append(store_id)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM [{S}].[POSSales] {where}"
        return pd.read_sql(sql, c, params=params)
    finally:
        if owned:
            c.close()


def get_account_calc(conn: pyodbc.Connection | None = None) -> pd.DataFrame:
    """
    Returns all rows from [Final].[AccountCalc].
    Columns: DestAccountID, SeqID, SourceAccountID, Multiplier
    """
    c, owned = _conn(conn)
    try:
        sql = f"SELECT * FROM [{S}].[AccountCalc] ORDER BY DestAccountID, SeqID"
        return pd.read_sql(sql, c)
    finally:
        if owned:
            c.close()
