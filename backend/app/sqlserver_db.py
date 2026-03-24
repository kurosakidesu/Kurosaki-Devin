"""SQL Server connection module for EC2-hosted DevinMockDB."""

import os
import logging
from contextlib import contextmanager
from typing import Generator

import pymssql

logger = logging.getLogger(__name__)

# Connection settings from environment variables
SQLSERVER_HOST = os.environ.get("SQLSERVER_HOST", "54.178.76.242")
SQLSERVER_PORT = int(os.environ.get("SQLSERVER_PORT", "1433"))
SQLSERVER_DB = os.environ.get("SQLSERVER_DB", "DevinMockDB")
SQLSERVER_USER = os.environ.get("SQLSERVER_USER", "sa")
SQLSERVER_PASSWORD = os.environ.get("SQLSERVER_PASSWORD", "1qaz2wsx")


def get_sqlserver_connection() -> pymssql.Connection:
    """Create a new SQL Server connection."""
    return pymssql.connect(
        server=SQLSERVER_HOST,
        port=SQLSERVER_PORT,
        user=SQLSERVER_USER,
        password=SQLSERVER_PASSWORD,
        database=SQLSERVER_DB,
        charset="UTF-8",
        login_timeout=10,
        timeout=30,
    )


@contextmanager
def get_sqlserver_db() -> Generator[pymssql.Connection, None, None]:
    """Context manager for SQL Server connection."""
    conn = get_sqlserver_connection()
    try:
        yield conn
    except Exception as e:
        logger.error("SQL Server error: %s", e)
        raise
    finally:
        conn.close()
