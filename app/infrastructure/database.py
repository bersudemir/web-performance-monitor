"""SQLAlchemy engine and session factory; no schema creation at import time."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.config import get_database_url

engine = create_engine(get_database_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
