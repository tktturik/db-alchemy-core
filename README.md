# dbalchemycore

**dbalchemycore** — это асинхронная библиотека для работы с базой данных PostgreSQL через SQLAlchemy Core. Она предоставляет удобный интерфейс для выполнения CRUD-операций, управления подключением к базе данных, миграциями через Alembic и асинхронными сессиями. Библиотека ориентирована на производительность, минимизацию дублирования кода и интеграцию с FastAPI и другими асинхронными фреймворками.

## Основные возможности

- **Асинхронные CRUD-операции**: Поддержка создания, чтения, обновления и удаления записей через обобщённый класс `BaseRepository`.
- **Pydantic-валидация**: Использование Pydantic-схем для фильтров, значений и агрегаций.
- **Поддержка миграций**: Интеграция с Alembic для управления схемой базы данных.
- **Управление транзакциями**: Декоратор `connection()` для автоматического управления асинхронными сессиями SQLAlchemy.
- **Гибкость**: Поддержка фильтрации, сортировки, пагинации, группировки и агрегаций (`count`, `sum`, `avg`, `min`, `max`).
- **Логирование**: Встроенное логирование операций и SQL-запросов для отладки.

## Установка

```bash
pip install dbalchemycore
```

Требуемые зависимости:
- `sqlalchemy[asyncpg]`
- `pydantic`
- `pydantic-settings`
- `alembic`

## Структура проекта

```text
project/
├── migration/                    # Директория для миграций Alembic
│   ├── versions/               # Файлы миграций
│   └── alembic.ini             # Конфигурация Alembic
├── dbAlchemyCore/              # Модуль библиотеки
│   ├── __init__.py             # Инициализация (init_db)
│   ├── models/                 # Модели SQLAlchemy
│   ├── schemas/                # Pydantic-схемы
│   ├── repositories/           # Репозитории для CRUD
│   ├── services/               # Бизнес-логика
│   └── utils/                  # Утилиты
├── .env                        # Переменные окружения
└── main.py                     # Точка входа
```

## Начало работы

1. **Настройка окружения**:
Создайте `.env` файл с параметрами подключения к базе данных:

```env
DB_USER=postgres
DB_PASSWORD=secret
DB_HOST=localhost
DB_PORT=5432
DB_NAME=mydb
DB_DRIVER=asyncpg
DB_DIALECT=postgresql
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50
DB_ECHO=False
DB_CONNECT_TIMEOUT=10
```

2. **Инициализация базы данных**:
Вызовите `init_db` один раз при старте приложения:

```python
import asyncio
from dbAlchemyCore import init_db

async def main():
    await init_db(migrations_path="alembic")

if __name__ == "__main__":
    asyncio.run(main())
```

3. **Создание модели**:
Модели должны наследоваться от `Base` и использовать `Mapped` для полей:

```python
# dbAlchemyCore/models/user.py
from sqlalchemy.orm import Mapped, mapped_column
from dbAlchemyCore import Base

class User(Base):
    name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str] = mapped_column(unique=True, nullable=False)
```

4. **Создание Pydantic-схем**:
Определите схемы для валидации данных:

```python
# dbAlchemyCore/schemas/user_schemas.py
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: str

class UserFilter(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
```

5. **Создание репозитория**:
Создайте класс репозитория, унаследованный от `BaseRepository`:

```python
# dbAlchemyCore/repositories/user_repo.py
from dbAlchemyCore.models.user import User
from dbAlchemyCore.repositories import BaseRepository

class UserRepo(BaseRepository):
    model = User
```

6. **Использование**:
Пример выполнения CRUD-операций:

```python
# main.py
import asyncio
from dbAlchemyCore import init_db
from dbAlchemyCore.repositories.user_repo import UserRepo
from dbAlchemyCore.schemas.user_schemas import UserCreate, UserFilter
from sqlalchemy.ext.asyncio import AsyncSession

async def main():
    await init_db(migrations_path="alembic")

    # Создание пользователя
    user_data = UserCreate(name="John", email="john@example.com")
    await UserRepo.create(values=user_data, session=session)

    # Получение пользователя
    user = await UserRepo.get_one(filters=UserFilter(name="John"), session=session)
    print(user)  # {"id": 1, "name": "John", "email": "john@example.com"}

if __name__ == "__main__":
    asyncio.run(main())
```

## Основные компоненты

### `init_db`
Инициализирует подключение к базе данных, создаёт движок `AsyncEngine` и фабрику сессий `async_sessionmaker`. Применяет миграции Alembic или создаёт таблицы.

**Параметры**:
- `migrations_path: str` — путь к директории миграций (например, `"alembic"`).

**Исключения**:
- `ConnectionRefusedError`: Сервер базы данных недоступен.
- `InvalidPasswordError`: Неверный пароль.
- `InvalidCatalogNameError`: Несуществующая база данных.
- `OperationalError`, `DatabaseError`, `InvalidRequestError`: Ошибки подключения SQLAlchemy.
- `CommandError`, `FileNotFoundError`: Ошибки миграций Alembic.

### `Base`
Базовый класс для моделей, автоматически добавляет поле `id` (первичный ключ) и генерирует имя таблицы (например, `users` для класса `User`).

### `BaseRepository`
Обобщённый класс для CRUD-операций. Поддерживает:
- **Методы**: `get_one`, `get_many`, `create`, `update`, `delete`, `execute_sql`.
- **Фильтры**: Через Pydantic-схемы, поддержка `IN` для списков (например, `role=["admin", "moderator"]`).
- **Сортировка**: Поддержка `order_by` с префиксом `-` для DESC.
- **Пагинация**: Параметры `limit` и `offset`.
- **Группировка и агрегация**: `group_by`, `aggregations` (`count`, `sum`, `avg`, `min`, `max`), `having_filters`.

**Исключения**:
- `NotFoundError`: Запись не найдена.
- `EmptyFilterError`: Пустые фильтры.
- `InvalidFieldError`: Несуществующее поле.
- `EmptyValueError`: Пустые значения для обновления.
- `UnknowAggregationFunc`: Неверная функция агрегации.
- `MultipleResultsFound`: Найдено несколько записей при `strict=True` в `get_one`.

### `connection()`
Декоратор для управления асинхронными сессиями в кастомных методах. Поддерживает настройку уровня изоляции (`isolation_level`) и коммита (`commit`).

**Пример**:
```python
from dbAlchemyCore.repositories import BaseRepository, connection
from sqlalchemy.ext.asyncio import AsyncSession

class UserRepo(BaseRepository):
    model = User

    @classmethod
    @connection(commit=True)
    async def get_user_orm(cls, id: int, session: AsyncSession):
        return await session.get(cls.model, id)
```

## Рекомендации

- **Модели**: Наследуйте от `Base`, используйте `Mapped` для полей.
- **Репозитории**: Создавайте отдельный класс для каждой модели, указывайте `model`.
- **Pydantic-схемы**: Используйте для валидации фильтров и значений, делайте поля опциональными для фильтрации/обновления.
- **Транзакции**: Применяйте `@connection()` для кастомных методов с доступом к базе.
- **Бизнес-логика**: Выносите сложную логику в модуль `services`.
- **Тестирование**: Используйте `pytest-asyncio` для асинхронных тестов, настройте тестовую БД (например, SQLite в памяти).

## Примечания

- **Асинхронность**: Все операции асинхронные, используют `AsyncSession` и `asyncpg`.
- **Ограничения**: `HAVING` требует `GROUP BY` (ограничение SQL). Фильтры не поддерживают сравнения (`>`, `<`, и т.д.).
- **Производительность**: Используйте SQLAlchemy Core для bulk-операций, избегайте смешивания с ORM для предотвращения stale data.
