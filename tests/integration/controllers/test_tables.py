import json
from http import HTTPStatus
from unittest.mock import Mock, patch
from uuid import uuid4

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.controllers.tables import TablesController
from pokerserver.database import TablesRelation, PlayersRelation
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future


class TestTablesController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_tables(self):
        table_1_id = 1
        table_2_id = 2
        await TablesRelation.create_table(table_1_id, 'table1', 9, "2s 3s 4s", 1, 2, "", 0, "", "frodo", "pippin",
                                          "pippin", "frodo", False)
        await TablesRelation.create_table(table_2_id, 'table2', 15, "7c 8s 9h", 1, 2, "", 0, "", "gandalf", "bilbo",
                                          "bilbo", "gandalf", False)
        await PlayersRelation.add_player(table_1_id, 0, "frodo", 10, "AcAd", 0)
        await PlayersRelation.add_player(table_1_id, 1, "pippin", 10, "KcKd", 0)
        await PlayersRelation.add_player(table_2_id, 0, "gandalf", 10, "AcAd", 0)
        await PlayersRelation.add_player(table_2_id, 1, "bilbo", 10, "KcKd", 0)

    @gen_test
    async def test_tables_response(self):
        await self.create_tables()
        response = await self.fetch_async('/tables')
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        response_data = json.loads(response_body)
        self.assertEqual(list(response_data.keys()), ['tables'])
        self.assertListEqual(response_data['tables'], [
            {
                'name': 'table1',
                'max_player_count': 9,
                'players': ['frodo', 'pippin']
            }, {
                'name': 'table2',
                'max_player_count': 15,
                'players': ['gandalf', 'bilbo']
            }
        ])

    @patch('pokerserver.models.table.Table.load_all')
    @patch('pokerserver.models.table.Table.create_tables', side_effect=return_done_future())
    @gen_test
    async def test_ensure_free_tables(self, create_tables, load_all):
        max_player_count = 4
        existing_tables = [Table(1, 'name', max_player_count, "", [], 1, 2, "", 0, [], "", "", "", "", False) for _ in range(5)]
        load_all.side_effect = return_done_future(existing_tables)

        await TablesController.ensure_free_tables(10, max_player_count)

        create_tables.assert_called_once_with(5, max_player_count)
