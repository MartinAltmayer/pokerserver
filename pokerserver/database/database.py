import logging
import sqlite3
import threading
from asyncio import Future, get_event_loop
from asyncio.tasks import gather
from collections import namedtuple
from datetime import datetime
from functools import partial
from queue import Queue

LOG = logging.getLogger(__name__)


class DbException(Exception):
    pass


class DuplicateKeyError(DbException):
    pass


class Database:
    POOL_SIZE = 4

    _instance = None

    @classmethod
    def instance(cls):
        return cls._instance

    def __init__(self, path, loop):
        self.path = path
        self._loop = loop
        self._queue = Queue()
        self._threads = []
        self.closed = False
        self.connected = False

    @classmethod
    async def connect(cls, path, loop=None):
        assert cls._instance is None, 'Must not connect to database twice'
        if loop is None:
            loop = get_event_loop()
        db = cls._instance = Database(path, loop)
        db.open_connection()
        return db

    def open_connection(self):
        assert not self.connected, 'This database is already connected'
        for _ in range(self.POOL_SIZE):
            connection = sqlite3.connect(self.path, check_same_thread=False)
            self._threads.append(threading.Thread(target=partial(self._run_in_thread, connection, self._queue)))
        self.connected = True
        for thread in self._threads:
            thread.start()

    async def close_connection(self):
        if not self.connected:
            return
        self.connected = False
        Database._instance = None

        futures = []
        for _ in range(self.POOL_SIZE):
            task = CloseTask(self._loop)
            futures.append(task.future)
            self._queue.put(task)

        await gather(*futures, loop=self._loop)
        self.closed = True

    def execute(self, query, *args):
        task = QueryTask(self._loop, query, *args)
        self._queue.put(task)
        return _ExecuteContextManager(task)

    async def find_one(self, query, *args):
        result = await self.execute(query, *args)
        return result.rows[0][0] if result.rows else None

    async def find_row(self, query, *args):
        result = await self.execute(query, *args)
        return result.rows[0] if result.rows else None

    @staticmethod
    def _run_in_thread(connection, queue):
        try:
            while True:
                task = queue.get()
                task.execute_and_resolve(connection)
                if isinstance(task, CloseTask):
                    return
        finally:
            connection.close()


class Task:
    def __init__(self, loop):
        self.loop = loop
        self.future = Future(loop=loop)
        self.result = None

    def execute(self, connection):
        raise NotImplementedError()

    def execute_and_resolve(self, connection):
        try:
            result = self.execute(connection)
            self.loop.call_soon_threadsafe(partial(self.future.set_result, result))
        except Exception as exc:  # pylint: disable=broad-except
            self.loop.call_soon_threadsafe(partial(self.future.set_exception, exc))


class CloseTask(Task):
    def execute(self, connection):
        connection.close()


class QueryTask(Task):
    def __init__(self, loop, query, *args):
        super().__init__(loop)
        self.query = query
        self.args = args

    def execute(self, connection):
        try:
            cursor = connection.execute(self.query, self.args)
        except sqlite3.IntegrityError as exc:
            connection.rollback()
            raise DuplicateKeyError(str(exc))
        except sqlite3.OperationalError as exc:
            connection.rollback()
            raise DbException(str(exc)) from exc

        connection.commit()
        result = QueryResult(rows=list(cursor), rowcount=cursor.rowcount)
        cursor.close()
        return result

    def __str__(self):
        return "<QUERY: {}, {}>".format(self.query, self.args)


QueryResult = namedtuple('QueryResult', 'rows rowcount')


# The stuff below is just to support the following pattern which was necessary while using aioodbc:
# async with db.execute(...) as cursor:
#     async for row in cursor:
#
# Implementing execute would be much easier without it

class _ExecuteContextManager:
    def __init__(self, task):
        self.task = task

    async def __aenter__(self):
        result = await self.task.future
        return FakeCursor(result)

    async def __aexit__(self, exc_type, exc, traceback):
        pass

    def __await__(self):
        return self.task.future.__await__()


class FakeCursor:
    def __init__(self, result):
        self._result = result
        self._index = 0

    async def fetchone(self):
        if self._index >= len(self._result.rows):
            return None
        row = self._result.rows[self._index]
        self._index += 1
        return row

    @property
    def rowcount(self):
        return self._result.rowcount

    def __aiter__(self):
        return self

    async def __anext__(self):
        value = await self.fetchone()
        if value is None:
            raise StopAsyncIteration()
        return value


def convert_datetime(db_string):
    if '.' in db_string:
        return datetime.strptime(db_string, "%Y-%m-%d %H:%M:%S.%f")
    return datetime.strptime(db_string, "%Y-%m-%d %H:%M:%S")
