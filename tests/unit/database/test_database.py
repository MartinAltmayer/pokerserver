from unittest.mock import patch, Mock

from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import Database


class TestDatabase(AsyncTestCase):
    async def async_setup(self):
        # Database.POOL_SIZE = 1
        with patch('pokerserver.database.database.sqlite3') as sqlite3_mock:
            sqlite3_mock.connect.return_value = self.build_connection_mock()
            await Database.connect('any/path/to.db')

    def build_connection_mock(self):
        cursor_mock = Mock()
        cursor_mock.__iter__ = Mock(return_value=iter([]))
        cursor_mock.rowcount = 0
        connection_mock = Mock()
        connection_mock.execute.return_value = cursor_mock
        return connection_mock

    @gen_test
    async def test_clear_database(self):
        await self.async_setup()
        await Database.instance().clear_tables()
