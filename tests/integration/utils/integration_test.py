import os
import tempfile

from asyncio.futures import Future
from tornado.platform.asyncio import AsyncIOLoop
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase

from pokerserver.database import Database


class IntegrationTestCase(AsyncTestCase):
    SETUP_DB_CONNECTION = True
    db = None
    _db_path = None

    @classmethod
    def setUpClass(cls):
        # It would be simpler and faster to use an in-memory database.
        # However, I couldn't figure out how to do this with aioodbc.
        _, cls._db_path = tempfile.mkstemp()

    @classmethod
    def tearDownClass(cls):
        if cls._db_path is not None and os.path.exists(cls._db_path):
            os.remove(cls._db_path)

    def setUp(self):
        self._tornado_loop = None
        super().setUp()
        if self.SETUP_DB_CONNECTION:
            self.db = self.get_asyncio_loop().run_until_complete(self.connect_database())
            self.get_asyncio_loop().run_until_complete(self.db.create_tables())

    def tearDown(self):
        if self.db is not None:
            self.get_asyncio_loop().run_until_complete(self.db.close())
            self.db = None
            os.truncate(self._db_path, 0)
        super().tearDown()

    def get_new_ioloop(self):
        assert self._tornado_loop is None, 'get_new_ioloop must not be called twice in one test case'
        self._tornado_loop = AsyncIOLoop()
        return self._tornado_loop

    def get_asyncio_loop(self):
        return self._tornado_loop.asyncio_loop

    async def connect_database(self):
        self.db = await Database.connect(self._db_path, loop=self.get_asyncio_loop())
        return self.db


class IntegrationHttpTestCase(IntegrationTestCase, AsyncHTTPTestCase):
    async def fetch_async(self, path):
        return await self.http_client.fetch(self.get_url(path))


def return_done_future(result=None):
    def future_creator(*args, **kwargs):
        future = Future()
        future.set_result(result)
        return future

    return future_creator