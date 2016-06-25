import asyncio
import aioodbc


class DbException(Exception):
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
        except Exception as exc:
            raise DbException('Creating database pool failed') from exc
        return db

    async def close(self):
        try:
            self._pool.close()
            await self._pool.wait_closed()
            Database._instance = None
        except Exception as exc:
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
        except Exception as exc:
            error = 'Executing query failed: {}'.format(self._query)
            await self._clear()
            raise DbException(error) from exc

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
                async with connection.cursor() as cursor:
                    await cursor.execute(self._query, *self._args)
                    await cursor.commit()
        except Exception as exc:
            raise DbException('Executing query failed: {}'.format(self._query)) from exc
