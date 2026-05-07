import sqlite3
from unittest.mock import Mock, patch

from scripts.check_backend_db import (
    REQUIRED_TABLES,
    check_backend_database,
    list_postgres_tables,
    list_sqlite_tables,
)


def test_list_sqlite_tables_returns_created_tables(tmp_path):
    db_path = tmp_path / "check.db"
    conn = sqlite3.connect(db_path)

    try:
        conn.execute("CREATE TABLE videos (id TEXT PRIMARY KEY);")
        conn.execute("CREATE TABLE runs (id TEXT PRIMARY KEY);")
        conn.commit()
    finally:
        conn.close()

    tables = list_sqlite_tables(f"sqlite:///{db_path}")

    assert "videos" in tables
    assert "runs" in tables


def test_check_backend_database_reports_missing_sqlite_tables(tmp_path):
    db_path = tmp_path / "partial.db"
    conn = sqlite3.connect(db_path)

    try:
        conn.execute("CREATE TABLE videos (id TEXT PRIMARY KEY);")
        conn.commit()
    finally:
        conn.close()

    missing = check_backend_database(f"sqlite:///{db_path}")

    assert "videos" not in missing
    assert "runs" in missing
    assert "audit_events" in missing


def test_check_backend_database_passes_when_all_required_sqlite_tables_exist(tmp_path):
    db_path = tmp_path / "complete.db"
    conn = sqlite3.connect(db_path)

    try:
        for table_name in REQUIRED_TABLES:
            conn.execute(f"CREATE TABLE {table_name} (id TEXT PRIMARY KEY);")
        conn.commit()
    finally:
        conn.close()

    missing = check_backend_database(f"sqlite:///{db_path}")

    assert missing == set()


def test_list_postgres_tables_queries_information_schema():
    database_url = "postgresql://user:password@example.com/neondb?sslmode=require"

    mock_cursor = Mock()
    mock_cursor.__enter__ = Mock(return_value=mock_cursor)
    mock_cursor.__exit__ = Mock(return_value=None)
    mock_cursor.fetchall.return_value = [
        ("videos",),
        ("runs",),
        ("audit_events",),
    ]

    mock_conn = Mock()
    mock_conn.__enter__ = Mock(return_value=mock_conn)
    mock_conn.__exit__ = Mock(return_value=None)
    mock_conn.cursor.return_value = mock_cursor

    with patch("scripts.check_backend_db.psycopg.connect", return_value=mock_conn) as mock_connect:
        tables = list_postgres_tables(database_url)

    assert tables == {"videos", "runs", "audit_events"}
    mock_connect.assert_called_once_with(database_url)
    mock_cursor.execute.assert_called_once()
    assert "information_schema.tables" in mock_cursor.execute.call_args.args[0]


def test_check_backend_database_reports_missing_postgres_tables():
    database_url = "postgresql://user:password@example.com/neondb?sslmode=require"

    with patch(
        "scripts.check_backend_db.list_postgres_tables",
        return_value={"videos", "runs", "audit_events"},
    ):
        missing = check_backend_database(database_url)

    assert "videos" not in missing
    assert "runs" not in missing
    assert "audit_events" not in missing
    assert "claims" in missing
    assert "evidence_records" in missing
