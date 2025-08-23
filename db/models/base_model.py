from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, declared_attr
from sqlalchemy.sql import func
from typing import Annotated
from sqlalchemy import String, Integer, DateTime


id_field = Annotated[int, mapped_column(Integer, primary_key=True, autoincrement=True)]
created_at = Annotated[DateTime, mapped_column(server_default=func.now())]
updated_at = Annotated[DateTime ,mapped_column(server_default=func.now(), onupdate=func.now())]


class Base(DeclarativeBase, AsyncAttrs):
    __abstract__ = True

    id: Mapped[id_field]

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'
    