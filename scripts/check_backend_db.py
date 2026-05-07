from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Set

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import psycopg

from src.backend.database_url import classify_database_url
from src.backend.settings import get_database_url


REQUIRED_TABLES = {
    "speakers",
    "videos",
    "claims",
    "evidence_records",
    "papers",
    "runs",
    "audit_events",
}


def _missing_tables(found_tables: Iterable[str]) -> set[str]:
    return REQUIRED_TABLES - set(found_tables)


def list_sqlite_tables(database_url: str) -> set[str]:
    database_info = classify_database_url(database_url)

    if database_info.kind != "sqlite":
        raise ValueError("list_sqlite_tables requires a SQLite database URL")

    db_path = database_info.database_name

    conn = sqlite3.connect(db_path)

    try:
        rows = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table';
            """
        ).fetchall()

        return {row[0] for row in rows}
    finally:
        conn.close()


def list_postgres_tables(database_url: str) -> set[str]:
    database_info = classify_database_url(database_url)

    if database_info.kind != "postgres":
        raise ValueError("list_postgres_tables requires a Postgres database URL")

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE';
                """
            )

            return {row[0] for row in cur.fetchall()}


def check_backend_database(database_url: str) -> Set[str]:
    database_info = classify_database_url(database_url)

    if database_info.kind == "sqlite":
        found_tables = list_sqlite_tables(database_url)
    elif database_info.kind == "postgres":
        found_tables = list_postgres_tables(database_url)
    else:
        raise RuntimeError(f"Unsupported database kind: {database_info.kind}")

    return _missing_tables(found_tables)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check whether the Inquiry Engine Week 6 backend database is initialized."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Optional database URL. If omitted, DATABASE_URL is read from .env/environment.",
    )

    args = parser.parse_args()

    database_url = args.database_url or get_database_url()
    database_info = classify_database_url(database_url)
    missing = check_backend_database(database_url)

    print("Backend database check complete.")
    print(f"Database kind: {database_info.kind}")
    print(f"Database name: {database_info.database_name}")

    if missing:
        print("Status: missing required tables")
        for table in sorted(missing):
            print(f"- {table}")
        raise SystemExit(1)

    print("Status: ok")
    print("All required Week 6 tables are present.")


if __name__ == "__main__":
    main()
