import logging
logger = logging.getLogger(__name__)
import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from db.models.base_model import Base
import os
import alembic.config




from functools import wraps
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.exc import OperationalError

from .config import settings



# module-level engine + sessionmaker — initialize lazily
_engine: Optional[AsyncEngine] = None
_async_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _make_engine() -> AsyncEngine:
    """Create AsyncEngine with sensible pool tuning for production.

    NOTE: tune pool_size / max_overflow to your workload and Postgres server limits.
    """
    global _engine
    if _engine is not None:
        return _engine

    url = settings.sqlalchemy_url
    logger.debug("Создание движка для базы данных: %s", url)

    connect_args = {"command_timeout": settings.DB_CONNECT_TIMEOUT}

    _engine = create_async_engine(
        url,
        echo=settings.DB_ECHO,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        connect_args=connect_args,
        future=True,
    )

    logger.info("Движок базы данных инициализирован для БД %s+%s://...", 
            settings.DB_DIALECT,settings.DB_DRIVER)
    return _engine



def _make_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _async_sessionmaker
    if _async_sessionmaker is not None:
        return _async_sessionmaker

    engine = _make_engine()
    _async_sessionmaker = async_sessionmaker(
        bind=engine, 
        expire_on_commit=False, 
        class_=AsyncSession
    )
    logger.debug("Создан асинхронный sessionmaker")
    return _async_sessionmaker



@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a session and handles rollback/close."""

    session_maker = _make_sessionmaker()
    async with session_maker() as session:
        logger.debug("Сессия базы данных создана")
        try:
            yield session
            logger.debug("Сессия завершена успешно")
        except SQLAlchemyError as exc:
            logger.debug("Ошибка в сессии: %s", str(exc))
            try:
                await session.rollback()
                logger.debug("Откат транзакции выполнен")
            except SQLAlchemyError as rollback_exc:
                logger.debug("Ошибка при откате транзакции: %s", rollback_exc)
            raise
        finally:
            await session.close()
            logger.debug("Сессия закрыта")
                
  

def connection(isolation_level: Optional[str] = None, commit: bool = True):
    """
    Декоратор для управления сессией с возможностью настройки уровня изоляции и коммита.

    Параметры:
    - `isolation_level`: уровень изоляции для транзакции (например, "SERIALIZABLE").
    - `commit`: если `True`, выполняется коммит после вызова метода.
    """

    def decorator(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            async with _async_sessionmaker() as session:
                logger.debug("Сессия создана в декораторе connection")
                try:
                    if isolation_level:
                        await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                        logger.debug("Установлен уровень изоляции: %s", isolation_level)


                    result = await method(*args, session=session, **kwargs)

                    if commit:
                        await session.commit()
                        logger.debug("Транзакция закоммичена")


                    return result
                except SQLAlchemyError as exc:
                    logger.debug("Ошибка в транзакции: %s", str(exc))
                    try:
                        await session.rollback()
                        logger.debug("Откат транзакции выполнен")
                    except SQLAlchemyError as rollback_exc:
                            logger.debug("Ошибка при откате: %s", str(rollback_exc))
                    raise
                finally:
                    await session.close()
                    logger.debug("Сессия в декораторе закрыта")


        return wrapper

    return decorator


# FastAPI dependency helper (if you use FastAPI)
async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    async with get_session() as session:
        logger.debug("Сессия создана для зависимости FastAPI")

        yield session


async def init_db(migrations_path: str = "alembic") -> None:
    """Ensure DB is reachable and initialize engine and sessionmaker."""

    _make_engine()
    _make_sessionmaker()

    if os.path.exists(os.path.join(migrations_path, "versions")):
        # есть миграции → запускаем Alembic
        alembic_cfg = alembic.config.Config(os.path.join(migrations_path, "alembic.ini"))
        script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
        head_revision = script.get_current_head()
        # Получаем объект head миграции
        head_migration = script.get_revision(head_revision)
        alembic.command.upgrade(alembic_cfg, "head")
        
        logger.info("Миграции alembic выполнены head: %s", head_migration)
    else:
        # миграций нет → делаем create_all
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Alembic не найден, таблицы созданы create_all()")

    logger.info("Database engine and sessionmaker initialized successfully.")