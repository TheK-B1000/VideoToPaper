import sqlite3
from pathlib import Path

import pytest

from src.backend.database_url import classify_database_url
from src.backend.db import (
    DEFAULT_POSTGRES_SCHEMA_PATH,
    DEFAULT_SQLITE_SCHEMA_PATH,
    DatabaseInitializationError,
    connect_sqlite,
    get_schema_path_for_database,
    initialize_database_from_url,
    initialize_sqlite_database,
    load_schema_sql,
    sqlite_path_from_url,
)


def test_get_schema_path_for_sqlite_database():
    database_info = classify_database_url("sqlite:///data/inquiry_engine.db")

    assert get_schema_path_for_database(database_info) == DEFAULT_SQLITE_SCHEMA_PATH


def test_get_schema_path_for_postgres_database():
    database_info = classify_database_url(
        "postgresql://user:password@example.com/neondb?sslmode=require"
    )

    assert get_schema_path_for_database(database_info) == DEFAULT_POSTGRES_SCHEMA_PATH


def test_sqlite_path_from_url_returns_file_path():
    db_path = sqlite_path_from_url("sqlite:///data/inquiry_engine.db")

    assert db_path == Path("data/inquiry_engine.db")


def test_sqlite_path_from_url_returns_memory_path():
    db_path = sqlite_path_from_url("sqlite:///:memory:")

    assert db_path == Path(":memory:")


def test_sqlite_path_from_url_rejects_postgres_url():
    with pytest.raises(DatabaseInitializationError):
        sqlite_path_from_url(
            "postgresql://user:password@example.com/neondb?sslmode=require"
        )


def test_load_schema_sql_reads_sqlite_schema_file():
    schema_sql = load_schema_sql(Path("src/backend/schema.sql"))

    assert "CREATE TABLE IF NOT EXISTS videos" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS runs" in schema_sql
    assert "CREATE TABLE IF NOT EXISTS audit_events" in schema_sql


def test_load_schema_sql_reads_postgres_schema_file():
    schema_sql = load_schema_sql(Path("src/backend/schema.postgres.sql"))

    assert "CREATE TABLE IF NOT EXISTS videos" in schema_sql
    assert "JSONB" in schema_sql
    assert "TIMESTAMPTZ" in schema_sql


def test_load_schema_sql_rejects_missing_file(tmp_path):
    missing_schema = tmp_path / "missing_schema.sql"

    with pytest.raises(DatabaseInitializationError):
        load_schema_sql(missing_schema)


def test_load_schema_sql_rejects_empty_file(tmp_path):
    empty_schema = tmp_path / "empty_schema.sql"
    empty_schema.write_text("", encoding="utf-8")

    with pytest.raises(DatabaseInitializationError):
        load_schema_sql(empty_schema)


def test_connect_sqlite_creates_parent_directory_and_enables_foreign_keys(tmp_path):
    db_path = tmp_path / "nested" / "inquiry_engine.db"

    conn = connect_sqlite(db_path)

    try:
        assert db_path.exists()

        foreign_keys_enabled = conn.execute(
            "PRAGMA foreign_keys;"
        ).fetchone()[0]

        assert foreign_keys_enabled == 1
    finally:
        conn.close()


def test_initialize_sqlite_database_creates_required_tables(tmp_path):
    db_path = tmp_path / "inquiry_engine.db"

    initialized_path = initialize_sqlite_database(
        db_path=db_path,
        schema_path=Path("src/backend/schema.sql"),
    )

    assert initialized_path == db_path
    assert initialized_path.exists()

    conn = sqlite3.connect(db_path)

    try:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name;
            """
        ).fetchall()

        table_names = {row[0] for row in rows}

        assert "videos" in table_names
        assert "speakers" in table_names
        assert "claims" in table_names
        assert "evidence_records" in table_names
        assert "papers" in table_names
        assert "runs" in table_names
        assert "audit_events" in table_names
    finally:
        conn.close()


def test_initialize_database_from_url_initializes_sqlite_database(tmp_path):
    db_path = tmp_path / "url_init.db"
    database_url = f"sqlite:///{db_path}"

    initialized_path = initialize_database_from_url(database_url)

    assert initialized_path == db_path
    assert initialized_path.exists()


def test_initialize_database_from_url_selects_postgres_schema_for_neon():
    database_url = "postgresql://user:password@example.com/neondb?sslmode=require"

    selected_path = initialize_database_from_url(database_url)

    assert selected_path == DEFAULT_POSTGRES_SCHEMA_PATH


def test_initialize_sqlite_database_preserves_foreign_key_constraints(tmp_path):
    db_path = tmp_path / "inquiry_engine.db"

    initialize_sqlite_database(
        db_path=db_path,
        schema_path=Path("src/backend/schema.sql"),
    )

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")

    try:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO claims (
                    id,
                    video_id,
                    verbatim_quote,
                    claim_type,
                    verification_strategy,
                    char_offset_start,
                    char_offset_end,
                    anchor_clip_start,
                    anchor_clip_end,
                    embed_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    "claim_orphan",
                    "video_missing",
                    "This claim has no parent video.",
                    "empirical_technical",
                    "literature_review",
                    0,
                    31,
                    1.0,
                    5.0,
                    "https://www.youtube-nocookie.com/embed/ABC123?start=1&end=5",
                ),
            )
    finally:
        conn.close()
