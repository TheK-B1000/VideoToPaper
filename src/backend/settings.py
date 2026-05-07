from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_PATH = PROJECT_ROOT / ".env"

load_dotenv(ENV_PATH)


def get_database_url() -> str:
    """
    Read the backend database URL from the environment.

    For local development, this should come from .env.
    For deployment, it should come from the hosting provider's secret manager.
    """
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add it to your local .env file."
        )

    return database_url
