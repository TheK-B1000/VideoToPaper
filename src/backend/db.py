from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from src.backend.database_url import DatabaseUrlInfo, classify_database_url


DEFAULT_SQLITE_DB_PATH = Path("data/inquiry_engine.db")
DEFAULT_SQLITE_SCHEMA_PATH = Path("src/backend/schema.sql")
DEFAULT_POSTGRES_SCHEMA_PATH = Path("src/backend/schema.postgres.sql")


class DatabaseInitializationError(RuntimeError):
    """Raised when the backend database cannot be initialized."""


def get_schema_path_for_database(database_info: DatabaseUrlInfo) -> Path:
    """
    Choose the correct schema file for the configured database.

    SQLite uses the lightweight local schema.
    Neon/Postgres uses the Postgres-native schema with JSONB and TIMESTAMPTZ.
    """
    if database_info.kind == "sqlite":
        return DEFAULT_SQLITE_SCHEMA_PATH

    if database_info.kind == "postgres":
        return DEFAULT_POSTGRES_SCHEMA_PATH

    raise DatabaseInitializationError(
        f"Unsupported database kind: {database_info.kind}"
    )


def sqlite_path_from_url(database_url: str) -> Path:
    """
    Convert a sqlite:/// URL into a local Path.

    Examples:
    - sqlite:///data/inquiry_engine.db -> data/inquiry_engine.db
    - sqlite:///:memory: -> :memory:
    """
    database_info = classify_database_url(database_url)

    if database_info.kind != "sqlite":
        raise DatabaseInitializationError(
            "sqlite_path_from_url only supports sqlite database URLs"
        )

    if database_info.database_name == ":memory:":
        return Path(":memory:")

    return Path(database_info.database_name)


def connect_sqlite(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """
    Create a SQLite connection with foreign key enforcement enabled.

    SQLite does not enforce foreign keys unless PRAGMA foreign_keys = ON
    is set per connection.
    """
    resolved_path = db_path or DEFAULT_SQLITE_DB_PATH

    if str(resolved_path) != ":memory:":
        resolved_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(resolved_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


def load_schema_sql(schema_path: Path) -> str:
    """
    Load a SQL schema file from disk.
    """
    if not schema_path.exists():
        raise DatabaseInitializationError(
            f"Schema file not found: {schema_path}"
        )

    schema_sql = schema_path.read_text(encoding="utf-8").strip()

    if not schema_sql:
        raise DatabaseInitializationError(
            f"Schema file is empty: {schema_path}"
        )

    return schema_sql


def initialize_sqlite_database(
    db_path: Optional[Path] = None,
    schema_path: Optional[Path] = None,
) -> Path:
    """
    Initialize a SQLite database using the SQLite schema.
    """
    resolved_db_path = db_path or DEFAULT_SQLITE_DB_PATH
    resolved_schema_path = schema_path or DEFAULT_SQLITE_SCHEMA_PATH
    schema_sql = load_schema_sql(resolved_schema_path)

    try:
        with connect_sqlite(resolved_db_path) as conn:
            conn.executescript(schema_sql)
    except sqlite3.DatabaseError as exc:
        raise DatabaseInitializationError(
            f"Failed to initialize SQLite database at {resolved_db_path}"
        ) from exc

    return resolved_db_path


def initialize_database_from_url(database_url: str) -> Path:
    """
    Initialize the configured database from DATABASE_URL.

    Currently:
    - SQLite URLs are initialized directly.
    - Postgres URLs return the selected schema path for migration tooling.

    The actual Neon execution step comes next using psycopg.
    """
    database_info = classify_database_url(database_url)
    schema_path = get_schema_path_for_database(database_info)

    if database_info.kind == "sqlite":
        sqlite_path = sqlite_path_from_url(database_url)
        return initialize_sqlite_database(
            db_path=sqlite_path,
            schema_path=schema_path,
        )

    if database_info.kind == "postgres":
        if not schema_path.exists():
            raise DatabaseInitializationError(
                f"Postgres schema file not found: {schema_path}"
            )

        return schema_path

    raise DatabaseInitializationError(
        f"Unsupported database kind: {database_info.kind}"
    )


# Backward-compatible aliases for older tests/imports.
connect_db = connect_sqlite
initialize_database = initialize_sqlite_database
