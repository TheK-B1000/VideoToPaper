from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.backend.db import DEFAULT_POSTGRES_SCHEMA_PATH, DatabaseInitializationError
from src.backend.postgres_db import (
    initialize_postgres_database,
    validate_postgres_database_url,
)


POSTGRES_URL = "postgresql://user:password@example.com/neondb?sslmode=require"


def test_validate_postgres_database_url_accepts_postgresql_url():
    assert validate_postgres_database_url(POSTGRES_URL) == POSTGRES_URL


def test_validate_postgres_database_url_accepts_postgres_alias():
    database_url = "postgres://user:password@example.com/neondb?sslmode=require"

    assert validate_postgres_database_url(database_url) == database_url


def test_validate_postgres_database_url_rejects_sqlite_url():
    with pytest.raises(DatabaseInitializationError):
        validate_postgres_database_url("sqlite:///data/inquiry_engine.db")


def test_initialize_postgres_database_executes_schema(tmp_path):
    schema_path = tmp_path / "schema.postgres.sql"
    schema_path.write_text(
        """
        CREATE TABLE IF NOT EXISTS test_table (
            id TEXT PRIMARY KEY
        );
        """,
        encoding="utf-8",
    )

    mock_cursor = Mock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_conn = Mock()
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor

    with patch("src.backend.postgres_db.psycopg.connect", return_value=mock_conn) as mock_connect:
        applied_schema_path = initialize_postgres_database(
            database_url=POSTGRES_URL,
            schema_path=schema_path,
        )

    assert applied_schema_path == schema_path
    mock_connect.assert_called_once_with(POSTGRES_URL)
    mock_cursor.execute.assert_called_once()
    assert "CREATE TABLE IF NOT EXISTS test_table" in mock_cursor.execute.call_args.args[0]
    mock_conn.commit.assert_called_once()


def test_initialize_postgres_database_defaults_to_week6_postgres_schema():
    mock_cursor = Mock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)

    mock_conn = Mock()
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor

    with patch("src.backend.postgres_db.psycopg.connect", return_value=mock_conn):
        applied_schema_path = initialize_postgres_database(database_url=POSTGRES_URL)

    assert applied_schema_path == DEFAULT_POSTGRES_SCHEMA_PATH
    mock_cursor.execute.assert_called_once()
    assert "CREATE TABLE IF NOT EXISTS videos" in mock_cursor.execute.call_args.args[0]
    assert "CREATE TABLE IF NOT EXISTS runs" in mock_cursor.execute.call_args.args[0]
    assert "CREATE TABLE IF NOT EXISTS audit_events" in mock_cursor.execute.call_args.args[0]


def test_initialize_postgres_database_rejects_missing_schema(tmp_path):
    missing_schema = tmp_path / "missing_schema.sql"

    with pytest.raises(DatabaseInitializationError):
        initialize_postgres_database(
            database_url=POSTGRES_URL,
            schema_path=missing_schema,
        )
