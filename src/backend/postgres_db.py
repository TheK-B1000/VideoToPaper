from __future__ import annotations

from pathlib import Path
from typing import Optional

import psycopg

from src.backend.database_url import classify_database_url
from src.backend.db import (
    DEFAULT_POSTGRES_SCHEMA_PATH,
    DatabaseInitializationError,
    load_schema_sql,
)


def validate_postgres_database_url(database_url: str) -> str:
    """
    Validate that the configured DATABASE_URL points to Postgres.

    Neon connection strings use postgresql:// or postgres:// and usually include
    sslmode=require.
    """
    database_info = classify_database_url(database_url)

    if database_info.kind != "postgres":
        raise DatabaseInitializationError(
            "Postgres initialization requires a postgres/postgresql DATABASE_URL"
        )

    return database_url


def connect_postgres(database_url: str) -> psycopg.Connection:
    """
    Open a psycopg connection to Neon/Postgres.
    """
    validated_url = validate_postgres_database_url(database_url)

    try:
        return psycopg.connect(validated_url)
    except psycopg.Error as exc:
        raise DatabaseInitializationError(
            "Failed to connect to Postgres database"
        ) from exc


def initialize_postgres_database(
    database_url: str,
    schema_path: Optional[Path] = None,
) -> Path:
    """
    Initialize Neon/Postgres using schema.postgres.sql.

    Returns the schema path that was applied.
    """
    validated_url = validate_postgres_database_url(database_url)
    resolved_schema_path = schema_path or DEFAULT_POSTGRES_SCHEMA_PATH
    schema_sql = load_schema_sql(resolved_schema_path)

    try:
        with psycopg.connect(validated_url) as conn:
            with conn.cursor() as cur:
                cur.execute(schema_sql)
            conn.commit()
    except psycopg.Error as exc:
        raise DatabaseInitializationError(
            "Failed to initialize Postgres database"
        ) from exc

    return resolved_schema_path
