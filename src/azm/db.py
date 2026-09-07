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


class ConnectionWrapper:
    """
    Wraps the database connection to seamlessly handle differences between
    SQLite (used for testing) and PostgreSQL (used for development/production).
    """
    def __init__(self, raw_conn, is_sqlite: bool):
        self.raw_conn = raw_conn
        self.is_sqlite = is_sqlite

    def execute(self, sql: str, params=None):
        if params is None:
            params = ()
        if self.is_sqlite:
            # SQLite uses '?' placeholders
            return self.raw_conn.execute(sql, params)
        else:
            # psycopg2 uses '%s' placeholders
            pg_sql = sql.replace("?", "%s")
            cur = self.raw_conn.cursor()
            cur.execute(pg_sql, params)
            return cur

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        self.raw_conn.close()


def get_connection(db_url: Optional[str] = None) -> ConnectionWrapper:
    """
    Return a connection wrapper to the AZM knowledge database.
    """
    url = db_url or AZM_DATABASE_URL
    
    if url.startswith("sqlite:///"):
        path = _parse_sqlite_path(url)
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return ConnectionWrapper(conn, is_sqlite=True)
        
    elif url.startswith("postgresql://") or url.startswith("postgres://"):
        try:
            import psycopg2
            from psycopg2.extras import DictCursor
        except ImportError:
            raise ImportError("psycopg2 is required to connect to PostgreSQL. Please install psycopg2 or psycopg2-binary.")
            
        conn = psycopg2.connect(url)
        conn.cursor_factory = DictCursor
        return ConnectionWrapper(conn, is_sqlite=False)
        
    else:
        raise ValueError(f"Unsupported database URL scheme: {url!r}")


def execute_schema(conn: ConnectionWrapper) -> None:
    """
    Execute the AZM schema DDL against an open connection.
    Idempotent: uses CREATE TABLE IF NOT EXISTS throughout.
    """
    schema_sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    
    if conn.is_sqlite:
        conn.raw_conn.executescript(schema_sql)
        conn.commit()
    else:
        # Strip SQLite-specific PRAGMA statements and execute for PostgreSQL
        lines = [line for line in schema_sql.split("\n") if not line.strip().startswith("PRAGMA")]
        clean_schema = "\n".join(lines)
        statements = []
        for stmt in clean_schema.split(";"):
            stmt = stmt.strip()
            if stmt:
                statements.append(stmt)
                
        with conn.raw_conn.cursor() as cur:
            for stmt in statements:
                cur.execute(stmt)
        conn.commit()


def is_initialized(conn: ConnectionWrapper) -> bool:
    """Return True if the AZM schema has been applied (azm_namespaces table exists)."""
    if conn.is_sqlite:
        cursor = conn.raw_conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='azm_namespaces'"
        )
        return cursor.fetchone() is not None
    else:
        with conn.raw_conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='azm_namespaces'"
            )
            return cur.fetchone() is not None
