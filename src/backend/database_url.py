from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from urllib.parse import urlparse


DatabaseKind = Literal["sqlite", "postgres"]


@dataclass(frozen=True)
class DatabaseUrlInfo:
    raw_url: str
    kind: DatabaseKind
    database_name: str


def classify_database_url(database_url: str) -> DatabaseUrlInfo:
    """
    Classify the configured database URL.

    Supported:
    - sqlite:///path/to/file.db
    - sqlite:///:memory:
    - postgresql://...
    - postgres://...

    Neon uses Postgres URLs, usually with sslmode=require.
    """
    if not database_url or not database_url.strip():
        raise ValueError("database_url cannot be empty")

    parsed = urlparse(database_url)
    scheme = parsed.scheme.lower()

    if scheme == "sqlite":
        database_name = parsed.path.lstrip("/") or ":memory:"
        return DatabaseUrlInfo(
            raw_url=database_url,
            kind="sqlite",
            database_name=database_name,
        )

    if scheme in {"postgresql", "postgres"}:
        database_name = parsed.path.lstrip("/")

        if not database_name:
            raise ValueError("Postgres database URL must include a database name")

        return DatabaseUrlInfo(
            raw_url=database_url,
            kind="postgres",
            database_name=database_name,
        )

    raise ValueError(f"Unsupported database URL scheme: {scheme}")
