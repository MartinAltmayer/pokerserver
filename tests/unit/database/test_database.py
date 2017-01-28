import unittest
from unittest.mock import patch, Mock

from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import Database, clear_relations


class TestDatabase(AsyncTestCase):
    async def async_setup(self):
        with patch('pokerserver.database.database.sqlite3') as sqlite3_mock:
            # pylint: disable=no-member
            sqlite3_mock.connect.return_value = self.build_connection_mock()
            await Database.connect('any/path/to.db')

    @staticmethod
    def build_connection_mock():
        cursor_mock = Mock()
        cursor_mock.__iter__ = Mock(return_value=iter([]))
        cursor_mock.rowcount = 0
        connection_mock = Mock()
        connection_mock.execute.return_value = cursor_mock
        return connection_mock

    @unittest.skip
    @gen_test
    async def test_clear_database(self):
        await self.async_setup()
        await clear_relations()
