import json
from http import HTTPStatus
from unittest.mock import Mock

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.database.tables import TablesTable
from tests.integration.utils.integration_test import IntegrationHttpTestCase


class TestTablesController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_tables(self):
        await TablesTable.create_table('table1', 9, ['frodo', 'pippin'])
        await TablesTable.create_table('table2', 15, ['gandlf', 'bilbo'])

    @gen_test
    async def test_tables_response(self):
        await self.create_tables()
        response = await self.fetch_async('/tables')
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        response_data = json.loads(response_body)
        self.assertEqual(list(response_data.keys()), ['tables'])
        self.assertListEqual(response_data['tables'], [
            {'name': 'table1', 'max_player_count': 9, 'players': ['frodo', 'pippin']},
            {'name': 'table2', 'max_player_count': 15, 'players': ['gandlf', 'bilbo']}
        ])
