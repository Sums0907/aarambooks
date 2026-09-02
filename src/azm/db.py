"""
AZM Database Connection Layer

Handles SQLite connection management and schema execution.
Raw sqlite3 — no ORM. PostgreSQL migration path: replace sqlite3 with psycopg2
and adjust the URL parsing logic.

AZM NEVER connects to Business System operational databases.
"""
import sqlite3
import os
import pathlib
from typing import Optional

from src.azm.config import AZM_DATABASE_URL

_SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"


def _parse_sqlite_path(url: str) -> str:
    """Extract file path from a 'sqlite:///...' URL."""
    if url.startswith("sqlite:///"):
        return url[len("sqlite:///"):]
    raise ValueError(f"Unsupported database URL scheme: {url!r}. Only 'sqlite:///' is supported in this build.")


def get_connection(db_url: Optional[str] = None) -> sqlite3.Connection:
    """
    Return a sqlite3 connection to the AZM knowledge database.
    Uses row_factory=sqlite3.Row so columns are accessible by name.
    """
    url = db_url or AZM_DATABASE_URL
    path = _parse_sqlite_path(url)

    # Ensure parent directory exists
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def execute_schema(conn: sqlite3.Connection) -> None:
    """
    Execute the AZM schema DDL against an open connection.
    Idempotent: uses CREATE TABLE IF NOT EXISTS throughout.
    """
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.commit()


def is_initialized(conn: sqlite3.Connection) -> bool:
    """Return True if the AZM schema has been applied (azm_namespaces table exists)."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='azm_namespaces'"
    )
    return cursor.fetchone() is not None
