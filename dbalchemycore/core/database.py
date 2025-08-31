import logging
import os
from contextlib import asynccontextmanager
from functools import wraps
from typing import AsyncGenerator, Optional

import alembic.config
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from dbalchemycore.models.base_model import Base

from .config import settings


logger = logging.getLogger(__name__)


_engine: Optional[AsyncEngine] = None
_async_sessionmaker: Optional[async_sessionmaker[AsyncSession]] = None


def _make_engine() -> AsyncEngine:
    """
    Создает и возвращает асинхронный движок для работы с базой данных.
    Инициализирует движок с настройками из конфигурации, использует пул соединений.

    Returns:
        AsyncEngine: Асинхронный движок SQLAlchemy для подключения к БД.
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

    logger.info(
        "Движок базы данных инициализирован для БД %s+%s://...",
        settings.DB_DIALECT,
        settings.DB_DRIVER,
    )
    return _engine


def _make_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """
    Создает и возвращает фабрику асинхронных сессий.
    Инициализирует sessionmaker с настроенным движком и параметрами сессий.

    Returns:
        async_sessionmaker[AsyncSession]: Фабрика для создания асинхронных сессий.
    """
    global _async_sessionmaker
    if _async_sessionmaker is not None:
        return _async_sessionmaker

    engine = _make_engine()
    _async_sessionmaker = async_sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    logger.debug("Создан асинхронный sessionmaker")
    return _async_sessionmaker


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный контекстный менеджер для получения сессии БД.
    Автоматически обрабатывает откат транзакций при ошибках и закрытие сессии.

    Yields:
        AsyncSession: Асинхронная сессия для работы с базой данных.

    Raises:
        SQLAlchemyError: При возникновении ошибок в работе с БД.
    """
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
    Декоратор для управления сессией БД с настройкой уровня изоляции и коммита.
    Обеспечивает автоматическое создание сессии, коммит и откат транзакций.

    Args:
        isolation_level: Уровень изоляции транзакции (например, "SERIALIZABLE").
        commit: Флаг необходимости коммита после выполнения метода.

    Returns:
        Декорированную функцию с управлением сессией.
    """

    def decorator(method):
        @wraps(method)
        async def wrapper(*args, **kwargs):
            async with _async_sessionmaker() as session:
                logger.debug("Сессия создана в декораторе connection")
                try:
                    if isolation_level:
                        await session.execute(
                            text(
                                f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"
                            )
                        )
                        logger.debug(
                            "Установлен уровень изоляции: %s", isolation_level
                        )

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
                        logger.debug(
                            "Ошибка при откате: %s", str(rollback_exc)
                        )
                    raise
                finally:
                    await session.close()
                    logger.debug("Сессия в декораторе закрыта")

        return wrapper

    return decorator


async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор зависимости для FastAPI, предоставляющий сессию БД.
    Используется как dependency injection в FastAPI роутах.

    Yields:
        AsyncSession: Асинхронная сессия для работы с базой данных.
    """
    async with get_session() as session:
        logger.debug("Сессия создана для зависимости FastAPI")

        yield session


async def init_db(migrations_path: str = "alembic") -> None:
    """
    Инициализирует подключение к БД, применяет миграции или создает таблицы.
    Проверяет наличие миграций Alembic и применяет их, либо создает таблицы через metadata.create_all.

    Args:
        migrations_path: Путь к директории с миграциями Alembic.

    """
    _make_engine()
    _make_sessionmaker()

    if os.path.exists(os.path.join(migrations_path, "versions")):
        alembic_cfg = alembic.config.Config(
            os.path.join(migrations_path, "alembic.ini")
        )
        script = alembic.script.ScriptDirectory.from_config(alembic_cfg)
        head_revision = script.get_current_head()
        head_migration = script.get_revision(head_revision)
        alembic.command.upgrade(alembic_cfg, "head")

        logger.info("Миграции alembic выполнены head: %s", head_migration)
    else:
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Alembic не найден, таблицы созданы create_all()")

    logger.info("Database engine and sessionmaker initialized successfully.")
