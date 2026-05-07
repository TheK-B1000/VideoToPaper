"""Smoke tests: DATABASE_URL from settings plus URL classification."""

from src.backend.database_url import classify_database_url
from src.backend.settings import get_database_url


def test_settings_url_classifies_as_sqlite_file(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///data/week6.db")

    info = classify_database_url(get_database_url())

    assert info.kind == "sqlite"
    assert info.database_name == "data/week6.db"


def test_settings_url_classifies_as_postgres(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:pass@ep-example.region.aws.neon.tech/neondb?sslmode=require",
    )

    info = classify_database_url(get_database_url())

    assert info.kind == "postgres"
    assert info.database_name == "neondb"
