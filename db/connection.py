"""
ODBC connection factory.

Usage:
    from db.connection import get_connection

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ...")
"""

import pyodbc
import config


def get_connection() -> pyodbc.Connection:
    """Return a new pyodbc connection using the configured DSN or connection string."""
    conn_str = config.ODBC_CONNECTION_STRING or f"DSN={config.ODBC_DSN}"
    return pyodbc.connect(conn_str)
