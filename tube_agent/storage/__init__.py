"""Storage backends - abstract interface with local and PostgreSQL implementations."""

from tube_agent.storage.base import StorageBackend
from tube_agent.storage.local import LocalStorage
from tube_agent.storage.postgres import PostgresStorage
from tube_agent.storage.composite import CompositeStorage
from tube_agent.storage.r2 import R2Storage
