"""FastAPI dependencies - database session, storage backend, settings."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from tube_agent.config import get_settings
from tube_agent.storage.postgres import PostgresStorage

_storage: PostgresStorage | None = None


def get_storage() -> PostgresStorage:
    """Get the singleton PostgresStorage instance."""
    global _storage
    if _storage is None:
        settings = get_settings()
        _storage = PostgresStorage(settings.database_url)
    return _storage


def get_db() -> Generator[Session, None, None]:
    """Yield a database session."""
    storage = get_storage()
    session = storage.get_session()
    try:
        yield session
    finally:
        session.close()
