import os

import pytest

from src.backend.settings import get_database_url


def test_get_database_url_reads_environment(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://user:password@example.com/db?sslmode=require",
    )

    assert get_database_url() == "postgresql://user:password@example.com/db?sslmode=require"


def test_get_database_url_raises_when_missing(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError):
        get_database_url()
