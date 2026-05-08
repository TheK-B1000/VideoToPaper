from pathlib import Path
from unittest.mock import patch

from scripts.init_backend_db import init_backend_database


def test_init_backend_database_uses_sqlite_path(tmp_path):
    db_path = tmp_path / "script_init.db"
    database_url = f"sqlite:///{db_path}"

    applied_path = init_backend_database(database_url)

    assert applied_path == db_path
    assert db_path.exists()


def test_init_backend_database_uses_postgres_initializer():
    database_url = "postgresql://user:password@example.com/neondb?sslmode=require"

    with patch(
        "scripts.init_backend_db.initialize_postgres_database",
        return_value=Path("src/backend/schema.postgres.sql"),
    ) as mock_initialize_postgres:
        applied_path = init_backend_database(database_url)

    assert applied_path == Path("src/backend/schema.postgres.sql")
    mock_initialize_postgres.assert_called_once_with(database_url)
