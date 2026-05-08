from __future__ import annotations

import argparse
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.backend.database_url import classify_database_url
from src.backend.db import initialize_database_from_url
from src.backend.postgres_db import initialize_postgres_database
from src.backend.settings import get_database_url


def init_backend_database(database_url: str) -> Path:
    """
    Initialize the backend database based on DATABASE_URL.

    SQLite is initialized locally.
    Postgres/Neon is initialized through psycopg.
    """
    database_info = classify_database_url(database_url)

    if database_info.kind == "sqlite":
        return initialize_database_from_url(database_url)

    if database_info.kind == "postgres":
        return initialize_postgres_database(database_url)

    raise RuntimeError(f"Unsupported database kind: {database_info.kind}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize the Inquiry Engine Week 6 backend database."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. If omitted, DATABASE_URL is read from .env/environment.",
    )

    args = parser.parse_args()

    database_url = args.database_url or get_database_url()
    database_info = classify_database_url(database_url)

    applied_path = init_backend_database(database_url)

    print("Backend database initialized.")
    print(f"Database kind: {database_info.kind}")
    print(f"Database name: {database_info.database_name}")
    print(f"Applied schema/source: {applied_path}")


if __name__ == "__main__":
    main()
