import json
from http import HTTPStatus
from unittest.mock import Mock, patch

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.controllers.tables import TablesController
from pokerserver.database import TablesRelation
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future


class TestTablesController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_tables(self):
        await TablesRelation.create_table('table1', 9, ['frodo', 'pippin'])
        await TablesRelation.create_table('table2', 15, ['gandlf', 'bilbo'])

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

    @patch('pokerserver.models.table.Table.load_all')
    @patch('pokerserver.models.table.Table.create_tables', side_effect=return_done_future())
    @gen_test
    async def test_ensure_free_tables(self, create_tables, load_all):
        max_player_count = 4
        existing_tables = [Table('name', max_player_count, []) for _ in range(5)]
        load_all.side_effect = return_done_future(existing_tables)

        await TablesController.ensure_free_tables(10, max_player_count)

        create_tables.assert_called_once_with(5, max_player_count)
