import json
from datetime import datetime
from http import HTTPStatus
from unittest.mock import Mock, patch

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.controllers.tables import TablesController
from pokerserver.database import TablesRelation, PlayersRelation
from pokerserver.database.tables import TableConfig
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future


class TestTablesController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_tables(self):
        table_1_id = 1
        table_2_id = 2
        config1 = TableConfig(4, 9, 1, 2)
        config2 = TableConfig(8, 15, 1, 2)
        await TablesRelation.create_table(
            table_1_id, 'table1', config1, ['2s', '3s', '4s'], [], 0, [], "frodo", "pippin", "pippin", "frodo", False)
        await TablesRelation.create_table(
            table_2_id, 'table2', config2, ['7c', '8s', '9h'], [], 0, [], "gandalf", "bilbo", "bilbo", "gandalf", False)
        timestamp = datetime.now()
        await PlayersRelation.add_player(table_1_id, 1, "frodo", 10, ['Ac', 'Ad'], 0, timestamp)
        await PlayersRelation.add_player(table_1_id, 2, "pippin", 10, ['Kc', 'Kd'], 0, timestamp)
        await PlayersRelation.add_player(table_2_id, 1, "gandalf", 10, ['Ac', 'Ad'], 0, timestamp)
        await PlayersRelation.add_player(table_2_id, 2, "bilbo", 10, ['Kc', 'Kd'], 0, timestamp)

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
                'min_player_count': 4,
                'max_player_count': 9,
                'players': {'1': 'frodo', '2': 'pippin'}
            }, {
                'name': 'table2',
                'min_player_count': 8,
                'max_player_count': 15,
                'players': {'1': 'gandalf', '2': 'bilbo'}
            }
        ])

    @patch('pokerserver.models.table.Table.load_all')
    @patch('pokerserver.models.table.Table.create_tables', side_effect=return_done_future())
    @gen_test
    async def test_ensure_free_tables(self, create_tables, load_all):
        config = TableConfig(min_player_count=2, max_player_count=4, small_blind=12, big_blind=24)
        existing_tables = [Table(i, 'name', config) for i in range(5)]
        load_all.side_effect = return_done_future(existing_tables)

        await TablesController.ensure_free_tables(10, config)

        create_tables.assert_called_once_with(5, config)
