from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, declared_attr
from sqlalchemy.sql import func
from typing import Annotated
from sqlalchemy import Integer, DateTime

# Аннотации для часто используемых полей
id_field = Annotated[int, mapped_column(Integer, primary_key=True, autoincrement=True)]
created_at = Annotated[DateTime, mapped_column(server_default=func.now())]
updated_at = Annotated[DateTime ,mapped_column(server_default=func.now(), onupdate=func.now())]


class Base(DeclarativeBase, AsyncAttrs):
    """
    Базовый класс для всех моделей SQLAlchemy.
    
    Предоставляет:
    - Автоматическое именование таблиц (имя класса в нижнем регистре + 's')
    - Автоматическое поле ID с автоинкрементом
    - Поддержку асинхронных операций через AsyncAttrs
    - Базовые временные метки created_at и updated_at
    """
    __abstract__ = True

    id: Mapped[id_field]    # Автоинкрементируемый первичный ключ

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Автоматически генерирует имя таблицы на основе имени класса."""
        return cls.__name__.lower() + 's'
    