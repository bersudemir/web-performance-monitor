"""Shared PostgreSQL configuration for SQLAlchemy and Alembic."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_database_url() -> URL:
    # Explicit environment variables take precedence over the project .env file.
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    required = ("POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        raise ValueError(f"Missing database settings: {', '.join(missing)}")

    port = int(os.environ.get("POSTGRES_PORT", "5432"))
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT must be between 1 and 65535")

    # URL.create handles special characters in credentials without interpolation.
    return URL.create(
        "postgresql+psycopg",
        username=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        host=os.environ.get("POSTGRES_HOST", "127.0.0.1"),
        port=port,
        database=os.environ["POSTGRES_DB"],
    )
