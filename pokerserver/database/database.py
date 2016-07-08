import asyncio
import logging
import aioodbc

LOG = logging.getLogger(__name__)


class DbException(Exception):
    pass


class DuplicateKeyError(DbException):
    pass


class Database:
    POOL_SIZE = 4

    _instance = None
    _pool = None

    @classmethod
    def instance(cls):
        return cls._instance

    @classmethod
    async def connect(cls, path, *, loop=None):
        # pylint: disable=protected-access
        assert cls._instance is None, 'Must not connect to database twice'
        dsn = 'Driver=SQLite3;Database={}'.format(path)
        if loop is None:
            loop = asyncio.get_event_loop()
        db = cls._instance = Database()
        try:
            db._pool = await aioodbc.create_pool(
                dsn=dsn, loop=loop, minsize=cls.POOL_SIZE, maxsize=cls.POOL_SIZE)
        except Exception as exc:  # pylint: disable=broad-except
            raise DbException('Creating database pool failed') from exc
        return db

    async def close(self):
        try:
            self._pool.close()
            await self._pool.wait_closed()
            Database._instance = None
        except Exception as exc:  # pylint: disable=broad-except
            raise DbException('Closing database pool failed') from exc

    @property
    def closed(self):
        return self._pool.closed

    async def create_table(self, table_class):
        await self.execute(table_class.CREATE_QUERY)

    async def create_tables(self):
        from ..database import RELATIONS
        for table_class in RELATIONS:
            await self.create_table(table_class)

    async def clear_tables(self, exclude=tuple()):
        from ..database import RELATIONS
        for table_class in RELATIONS:
            if table_class.NAME not in exclude:
                await self.execute('DELETE FROM {}'.format(table_class.NAME))

    def execute(self, query, *args):
        return _ExecuteContextManager(self._pool, query, *args)

    async def find_row(self, query, *args):
        async with self.execute(query, *args) as cursor:
            row = await cursor.fetchone()
            return tuple(row) if row is not None else None

    async def find_one(self, query, *args):
        row = await self.find_row(query, *args)
        return row[0] if row is not None else None


class _ExecuteContextManager:
    def __init__(self, pool, query, *args):
        self._pool = pool
        self._conn = None
        self._cursor = None
        self._query = query
        self._args = args

    async def __aenter__(self):
        try:
            self._conn = await self._pool.acquire()
            self._cursor = await self._conn.cursor()
            await self._cursor.execute(self._query, *self._args)
            await self._cursor.commit()
            return self._cursor
        except Exception as exc:  # pylint: disable=broad-except
            await self._clear()
            self._handle_query_exception(exc)

    async def _clear(self):
        if not self._cursor.closed:
            await self._cursor.close()
        await self._pool.release(self._conn)
        self._pool = None
        self._conn = None
        self._cursor = None

    async def __aexit__(self, exc_type, exc, traceback):
        await self._clear()

    def __await__(self):
        return self._coroutine().__await__()

    async def _coroutine(self):
        try:
            async with self._pool.acquire() as connection:
                try:
                    async with connection.cursor() as cursor:
                        await cursor.execute(self._query, *self._args)
                        await cursor.commit()
                except Exception:  # pylint: disable=broad-except
                    # aioodbc deadlocks if we do not close the connection (the cursor is already closed)
                    # We must close the connection before releasing it, otherwise it is added to the pool again.
                    await connection.close()
                    raise
        except Exception as exc:  # pylint: disable=broad-except
            self._handle_query_exception(exc)

    def _handle_query_exception(self, exc):
        LOG.error("Executing query failed: %s %s", exc, self._query)
        if 'unique' in str(exc).lower():  # I could not find a proper way for this check
            raise DuplicateKeyError('Query: {}'.format(self._query)) from exc
        else:
            raise DbException('Executing query failed. Exception: {}. Query: {} Args: {}'
                              .format(exc, self._query, self._args)) from exc
