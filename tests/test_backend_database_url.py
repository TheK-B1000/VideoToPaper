import pytest

from src.backend.database_url import classify_database_url


def test_classify_sqlite_file_database_url():
    info = classify_database_url("sqlite:///data/inquiry_engine.db")

    assert info.kind == "sqlite"
    assert info.database_name == "data/inquiry_engine.db"
    assert info.raw_url == "sqlite:///data/inquiry_engine.db"


def test_classify_sqlite_memory_database_url():
    info = classify_database_url("sqlite:///:memory:")

    assert info.kind == "sqlite"
    assert info.database_name == ":memory:"


def test_classify_postgresql_database_url():
    info = classify_database_url(
        "postgresql://user:password@example.com/inquiry_engine?sslmode=require"
    )

    assert info.kind == "postgres"
    assert info.database_name == "inquiry_engine"


def test_classify_postgres_database_url_alias():
    info = classify_database_url(
        "postgres://user:password@example.com/neondb?sslmode=require"
    )

    assert info.kind == "postgres"
    assert info.database_name == "neondb"


def test_rejects_empty_database_url():
    with pytest.raises(ValueError, match="database_url cannot be empty"):
        classify_database_url("")


def test_rejects_unsupported_database_url_scheme():
    with pytest.raises(ValueError, match="Unsupported database URL scheme"):
        classify_database_url("mysql://user:password@example.com/db")


def test_rejects_postgres_url_without_database_name():
    with pytest.raises(ValueError, match="must include a database name"):
        classify_database_url("postgresql://user:password@example.com")
