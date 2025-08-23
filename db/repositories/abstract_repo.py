import logging
logger = logging.getLogger(__name__)
from typing import Generic, TypeVar, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import Row, RowMapping, select, text, update, delete,insert
from sqlalchemy.orm import DeclarativeMeta
from db.models.base_model import Base
from db.core.database import connection
from sqlalchemy import select, func, distinct, and_, or_, text
from sqlalchemy.exc import MultipleResultsFound, NoResultFound
from typing import Optional, List, Dict, Any, Union, Type, Set
from sqlalchemy.sql import Select
from db.core.exc import *
import time


from pydantic import BaseModel


T = TypeVar("T", bound=Base)  # Тип модели

class BaseRepository(Generic[T]):
    """Базовый класс репозитория с реализацией CRUD операций."""
    model: type[T]
    _model_columns_map: Dict[str, Any] = {}
    
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'model') and cls.model is not None:
            cls._init_model_columns()
            logger.debug("Инициализированы колонки модели для %s", cls.model.__name__)
    
    @classmethod
    def _init_model_columns(cls):
        """Инициализация маппинга колонок с label"""
        cls._model_columns_map = {
            field: getattr(cls.model, field).label(field)
            for field in cls.model.__table__.columns.keys()
        }
        logger.debug("Создан маппинг колонок с %d полями", len(cls._model_columns_map))


    @classmethod
    def _get_model_columns(cls) -> Dict[str, Any]:
        """Получить словарь колонок {имя: колонка.label(имя)}"""
        if not hasattr(cls, "_model_columns_map") or cls._model_columns_map is None:
            cls._init_model_columns()
        return cls._model_columns_map

    @classmethod
    @connection()
    async def execute_sql(cls, stmt: str, session: AsyncSession) -> List[Dict]:
        """Выполнить произвольный SQL-запрос и вернуть результат в виде списка словарей.
        
        Args:
            stmt: SQL-запрос в виде строки
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            List[Dict]: Список строк, где каждая строка представлена словарем
        """
        start_time = time.time()
        logger.debug("Выполнение самописного SQL запроса, длина: %d символов", len(stmt))
    
        result = await session.execute(text(stmt))
        
        logger.debug("SQL выполнен за %.3f сек", _count_execute_time(start_time=start_time))
            
        return [dict(row) for row in result.mappings()]
        
    

    @classmethod
    @connection(commit=False)
    async def get_one(
        cls,
        id: Optional[int] = None,
        filters: Optional[BaseModel] = None,
        select_fields: Optional[List[str]] = None,
        order_by: Optional[Union[str, List[str]]] = None,
        strict: bool = True,
        session: AsyncSession = None
    ) -> Optional[Dict[str, Any]]:
        """
        Получить одну запись в виде словаря.
        
        Args:
            id: ID записи для поиска
            filters: Pydantic модель с фильтрами равенства
            select_fields: Список полей для выборки
            order_by: Поле(я) для сортировки. Для DESC добавить префикс '-'
            strict: Если True, выбросит исключение при множественных результатах
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            Optional[Dict[str, Any]]: Словарь с данными записи или None если не найдено
            
        Raises:
            MultipleResultsFound: Если strict=True и найдено более одной записи
        """
        start_time = time.time()
        logger.debug("Вызов get_one - ID: %s, strict: %s", id, strict)

        # Оптимизация для запроса по ID
        if id is not None and filters is None and select_fields is None and order_by is None:
            logger.debug("Оптимизированный путь запроса по ID")
            columns = list(cls._get_model_columns().values())
            stmt = select(*columns).where(cls.model.id == id)
            result = await session.execute(stmt)
            mapping = result.mappings().one_or_none()  # Возвращает None если ничего не найдено

            if mapping is None:
                logger.debug("Найдена запись по ID за %.3f сек", _count_execute_time(start_time=start_time))
                return None
            else:
                logger.debug("Запись не найдена по ID за %.3f сек", _count_execute_time(start_time=start_time))

            return dict(mapping)

        # Базовый запрос
        query = cls._build_select_query(select_fields)
        if id is not None:
            query = query.where(cls.model.id == id)
        if filters:
            query = cls._apply_filters(query, filters)
        if order_by:
            query = cls._apply_ordering(query, order_by)

        # Выполняем запрос
        if strict:
            result = await session.execute(query)
            mappings = result.mappings().all()  # Fetch all для проверки
            if len(mappings) > 1:
                raise MultipleResultsFound(f"Найдено несколько строк, ожидалась только 1 для {cls.model.__name__}")
            mapping = mappings[0] if mappings else None
        else:
            # Для non-strict — limit 1
            query = query.limit(1)
            result = await session.execute(query)
            mapping = result.mappings().first()
        logger.debug("get_one завершен за %.3f сек, найдено: %s", 
                    _count_execute_time(start_time=start_time), mapping is not None)

        return dict(mapping) if mapping is not None else None


    @classmethod
    @connection(commit=False)
    async def get_many(
        cls,
        filters: Optional[BaseModel] = None,
        select_fields: Optional[List[str]] = None,
        order_by: Optional[Union[str, List[str]]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        is_distinct: bool = False,
        group_by: Optional[Union[str, List[str]]] = None,
        having_filters: Optional[BaseModel] = None,
        aggregations: Optional[Dict[str, str]] = None,
        session: AsyncSession = None
    ) -> List[Dict[str, Any]]:
        """
        Получить множество записей в виде списка словарей.
        
        Args:
            filters: Pydantic модель с фильтрами равенства
            select_fields: Список полей для выборки (игнорируется при group_by)
            order_by: Поле(я) для сортировки. Для DESC добавить префикс '-'
            limit: Максимальное количество записей
            offset: Смещение для пагинации
            is_distinct: Использовать DISTINCT для уникальных значений (игнорируется при group_by)
            group_by: Поле(я) для группировки (при указании select_fields игнорируется)
            having_filters: Фильтры для HAVING (после группировки)
            aggregations: Словарь агрегатных функций {'field': 'func'} где func: count, sum, avg, min, max
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            List[Dict[str, Any]]: Список словарей с данными записей
        """
        start_time = time.time()
        logger.debug("Вызов get_many - лимит: %s, distinct: %s", limit, is_distinct)
        # Переменные для хранения ключей результата
        expected_keys = []
        
        # Строим базовый запрос с учетом группировки
        if group_by or aggregations:
            logger.debug("Использование группированного запроса")
            query = cls._build_grouped_query(group_by, aggregations)
            # Для группировки получим ключи из первой строки результата
            expected_keys = None  # Определим позже из результата
        else:
            # Обычный запрос - всегда получаем сырые данные для словарей
            if select_fields:
                # Валидируем поля используя множество полей модели
                if hasattr(cls, '_validate_fields'):
                    valid_fields = cls._validate_fields(select_fields)
                else:
                    # Простая валидация через множество полей
                    model_fields = cls._get_model_columns().keys()
                    valid_fields = [field for field in select_fields if field in model_fields]
                    if not valid_fields:
                        raise ValueError(f"No valid fields found in select_fields: {select_fields}")
                
                columns_map = cls._get_model_columns()
                columns = [columns_map[field] for field in valid_fields]

                expected_keys = valid_fields
                
                if is_distinct:
                    query = select(distinct(*columns))
                else:
                    query = select(*columns)
            else:
                # Выбираем все поля из множества _model_fields
                columns_map = cls._get_model_columns()
                columns = list(columns_map.values())
                expected_keys = list(columns_map.keys())

                
                if is_distinct:
                    query = select(distinct(*columns))
                else:
                    query = select(*columns)
        
        # Применяем фильтры и другие параметры
        if filters:
            query = cls._apply_filters(query, filters)
        if group_by:
            query = cls._apply_grouping(query, group_by)
        if having_filters and group_by:
            query = cls._apply_having_filters(query, having_filters)
        if order_by:
            query = cls._apply_ordering(query, order_by)
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        
        # Выполняем запрос
        result = await session.execute(query)
        rows = result.all()
        logger.debug("get_many завершен за %.3f сек, найдено %d строк", 
                    _count_execute_time(start_time=start_time), len(rows))
        if not rows:
            return []
        
        # Определяем ключи для создания словарей
        if expected_keys is None:
            # Для группировки или агрегации - получаем ключи из первой строки
            if hasattr(rows[0], '_mapping'):
                expected_keys = list(rows[0]._mapping.keys())
            else:
                # Fallback: пытаемся получить имена полей из результата
                expected_keys = list(range(len(rows[0]))) if rows[0] else []
        
        # Создаем список словарей
        result_dicts = []
        for row in rows:
            if hasattr(row, '_mapping'):
                mapping_dict = dict(row._mapping)
                # Исправляем ключ _no_label на правильное имя поля
                if '_no_label' in mapping_dict and len(expected_keys) == 1:
                    # Если есть _no_label и ожидается только одно поле
                    correct_key = expected_keys[0]
                    mapping_dict[correct_key] = mapping_dict.pop('_no_label')
                
                result_dicts.append(mapping_dict)
            else:
                # Для обычных результатов создаем словарь из ключей и значений
                result_dicts.append(dict(zip(expected_keys, row)))
        
        return result_dicts

            
    @classmethod
    def _build_select_query(cls, select_fields: Optional[List[str]] = None, use_distinct: bool = False) -> Select:
        """Построение базового SELECT запроса"""
        if select_fields:
            # Проверяем существование полей
            valid_fields = cls._validate_fields(select_fields)
            columns_map = cls._get_model_columns()
            columns = [columns_map[field] for field in valid_fields]            
            if use_distinct:
                query = select(distinct(*columns))
            else:
                query = select(*columns)
        else:
            # Используем все поля из множества _model_fields
            columns_map = cls._get_model_columns()
            columns = list(columns_map.values())            
            if use_distinct:
                query = select(distinct(*columns))
            else:
                query = select(*columns)
                
        return query

    @classmethod
    def _build_grouped_query(
        cls, 
        group_by: Optional[Union[str, List[str]]] = None,
        aggregations: Optional[Dict[str, str]] = None
    ) -> Select:
        """
        Построение запроса с группировкой и агрегатными функциями.
        В SELECT попадают только поля из group_by + агрегатные функции.
        """
        columns = []
        
        # Добавляем поля группировки
        if group_by:
            if isinstance(group_by, str):
                group_by = [group_by]
                
            valid_group_fields = cls._validate_fields(group_by)
            columns_map = cls._get_model_columns()
            columns.extend([columns_map[field].element for field in valid_group_fields])
        
        # Добавляем агрегатные функции
        if aggregations:
            model_fields = cls._get_model_columns().keys()
            for field, func_name in aggregations.items():
                if field in model_fields:
                    column = cls._get_model_columns()[field].element
                    
                    if func_name.lower() == 'count':
                        columns.append(func.count(column).label(f"{field}_{func_name}"))
                    elif func_name.lower() == 'sum':
                        columns.append(func.sum(column).label(f"{field}_{func_name}"))
                    elif func_name.lower() == 'avg':
                        columns.append(func.avg(column).label(f"{field}_{func_name}"))
                    elif func_name.lower() == 'min':
                        columns.append(func.min(column).label(f"{field}_{func_name}"))
                    elif func_name.lower() == 'max':
                        columns.append(func.max(column).label(f"{field}_{func_name}"))
                    else:
                        raise UnknowAggregationFunc(f"Неизвестная функция агрегации {func_name.lower}")
            if not columns:
                # Если нет ни группировки, ни агрегаций - возвращаем все поля
                columns = list(cls._get_model_columns().values())

            
        return select(*columns)

    @classmethod
    def _apply_filters(cls, query: Select, filters: BaseModel) -> Select:
        """Применение фильтров равенства"""
        conditions = cls._build_conditions(filter=filters)    
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    


    @classmethod
    def _apply_ordering(cls, query: Select, order_by: Union[str, List[str]]) -> Select:
        """Применение сортировки"""
        if isinstance(order_by, str):
            order_by = [order_by]
        
        model_fields = cls._get_model_columns().keys()
        
        for order_field in order_by:
            desc = False
            
            # Проверяем префикс для DESC
            if order_field.startswith('-'):
                desc = True
                order_field = order_field[1:]
            
            if order_field in model_fields:
                column = cls._get_model_columns()[order_field].element
                
                if desc:
                    query = query.order_by(column.desc())
                else:
                    query = query.order_by(column.asc())
        
        return query

    @classmethod
    def _apply_grouping(cls, query: Select, group_by: Union[str, List[str]]) -> Select:
        """Применение группировки"""
        if isinstance(group_by, str):
            group_by = [group_by]
        
        group_columns = []
        model_fields = cls._get_model_columns().keys()
        
        for field in group_by:
            if field in model_fields:
                group_columns.append(cls._get_model_columns()[field].element)
        
        if group_columns:
            query = query.group_by(*group_columns)
        
        return query

    @classmethod
    def _apply_having_filters(cls, query: Select, having_filters: BaseModel) -> Select:
        """Применение HAVING фильтров после группировки"""
        filter_dict = having_filters.model_dump(exclude_unset=True)
        having_conditions = []
        model_fields = cls._get_model_columns().keys()
        
        for field, value in filter_dict.items():
            if field in model_fields:
                column = cls._get_model_columns()[field].element
                having_conditions.append(column == value)
        
        if having_conditions:
            query = query.having(and_(*having_conditions))
        
        return query

    @classmethod
    def _validate_fields(cls, fields: List[str]) -> List[str]:
        """Валидация существования полей в модели"""
        valid_fields = []
        model_fields = cls._get_model_columns().keys()
        for field in fields:
            if field in model_fields:
                valid_fields.append(field)
            else:
                raise InvalidFieldError(f"Поле {field} отсутствует в модели {str(cls.model)}")
        return valid_fields
    
    @classmethod
    def _build_conditions(
        cls, 
        filter: BaseModel, 
    ) -> List[Any]:
        """
        Построение условий фильтрации из схемы.
        
        Args:
            filter: Схема с полями и значениями для фильтрации
            
        Returns:
            List[Any]: Список условий для WHERE
            
        Raises:
            InvalidFieldError: Если найдено хоть одно невалидное поле
        """

        filter_dict = filter.model_dump(exclude_unset=True)
   
        model_fields = cls._get_model_columns()
        conditions = []
        
        for field, value in filter_dict.items():
            if field in model_fields:
                column = model_fields[field].element
                
                if isinstance(value, list):
                    # Фильтр IN для списков
                    if len(value) == 0:
                        continue  # Пропускаем пустые списки
                    conditions.append(column.in_(value))
                else:
                    conditions.append(column == value)
            else:
                raise InvalidFieldError(f"Поле '{field}' не найдено в модели {str(cls.model)}")
        return conditions

    @classmethod
    @connection()
    async def create(
        cls, 
        values: Union[BaseModel, List[BaseModel]], 
        session: AsyncSession
    ) -> int:
        """
        Создает одну или несколько записей в базе данных через insert DSL.
        
        Args:
            values: BaseModel для одной записи или List[BaseModel] для нескольких записей
            session: Асинхронная сессия SQLAlchemy
            
        Returns:
            Количество созданных записей (int)
        """
        start_time = time.time()

        # Приводим всё к списку словарей
        if isinstance(values, BaseModel):
            values_dicts = [values.model_dump(exclude_unset=True)]
            logger.debug("Создание одной записи")
        else:
            values_dicts = [v.model_dump(exclude_unset=True) for v in values]
            logger.debug("Создание %d записей батчем", len(values_dicts))

        # Формируем один батч-запрос
        stmt = insert(cls.model).values(values_dicts)

        result = await session.execute(stmt)
        execution_time = time.time() - start_time
        logger.debug("Создано %d записей за %.3f сек", result.rowcount, execution_time)

        return result.rowcount
            

    @classmethod
    @connection()
    async def delete(
        cls, 
        session: AsyncSession, 
        id: int = None, 
        filters: BaseModel = None
    ) -> int:
        
        """
        Удалить записи по переданным параметрам.
        
        :param session: Асинхронная сессия SQLAlchemy.
        :param id: ID записи для удаления (приоритетный параметр).
        :param filter: Модель с фильтрами для удаления.
        :return: True, если записи были удалены, иначе Exception.
        """

        start_time = time.time()

        # Удаление по ID (приоритет)
        if id is not None:
            logger.debug("Вызов delete - ID: %s, фильтр: %s", id, repr(filters))
            stmt = delete(cls.model).where(cls.model.id == id)
            result = await session.execute(stmt)

            if result.rowcount > 0:
                logger.debug("Удалено %d записей по ID за %.3f сек", 
                result.rowcount, _count_execute_time(start_time=start_time))
                return result.rowcount
            else:
                raise NotFoundError(f"Запись по id={id} не найдена")
        # Удаление по фильтрам
        if filters is not None:
            
            conditions = cls._build_conditions(filter=filters)
            
            # Выполняем удаление с условиями
            stmt = delete(cls.model).where(*conditions)
            result = await session.execute(stmt)

            if result.rowcount > 0:
                logger.debug("Удалено %d записей по фильтру за %.3f сек", 
                result.rowcount, _count_execute_time(start_time=start_time))
                return result.rowcount
            else:
                raise NotFoundError(f"Записи для удаления по фильтрам {filters} не найдены")
        else:
            raise EmptyFilterError("Не переданы параметры для удаления")



    @classmethod
    @connection()
    async def update(
        cls,
        session: AsyncSession,
        values: BaseModel,
        id: int = None,
        filters: BaseModel = None
    ) -> int:
        """
        Универсальный метод для обновления записей одинаковыми значениями.
        
        :param session: Асинхронная сессия SQLAlchemy.
        :param values: Модель с новыми значениями для обновления.
        :param id: ID записи для обновления (приоритетный параметр).
        :param filter_criteria: Модель с критериями для фильтрации записей.
        :return: Количество обновленных записей.
        """
        start_time = time.time()
        logger.debug("Вызов update - ID: %s, есть_фильтр: %s", id, repr(filters))
        # Валидация входных данных
        values_dict = values.model_dump(exclude_unset=True)
        if not values_dict:
            raise EmptyValueError("Не переданы значения для обновления")
        
        # Обновление по ID (приоритет)
        if id is not None:
            stmt = (
                update(cls.model)
                .where(cls.model.id == id)
                .values(**values_dict)
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                raise NotFoundError(f"Запись с id={id} не найдена")
            logger.debug("Обновлено %d записей по ID за %.3f сек", 
            result.rowcount, _count_execute_time(start_time=start_time))
            return result.rowcount
        
        # Массовое обновление по критериям
        if filters is not None:

            conditions = cls._build_conditions(filter=filters)
        
            # Выполняем обновление с условиями
            stmt = (
                update(cls.model)
                .where(*conditions)
                .values(**values_dict)
            )
            
            result = await session.execute(stmt)

            if result.rowcount == 0:
                raise NotFoundError(f"Записи для обновления по фильтрам {filters} не найдены")
            
            logger.debug("Обновлено %d записей по фильтру за %.3f сек", 
            result.rowcount, _count_execute_time(start_time=start_time))
            return result.rowcount
        else:
            raise EmptyFilterError("Не переданы критерии для обновления (id или filter_criteria)")


def _count_execute_time(start_time: float):
    return time.time() - start_time
