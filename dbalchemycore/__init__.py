# src/my_db_library/__init__.py
from .core.config import settings
from .core.database import connection, init_db
from .models.base_model import Base
from .repositories.abstract_repo import BaseRepository

__version__ = "0.1.4"
__all__ = ["settings", "connection", "init_db", "Base", "BaseRepository"]
