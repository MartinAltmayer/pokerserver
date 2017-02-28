from datetime import datetime
from http import HTTPStatus
import json
from unittest.mock import Mock

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.database import PlayerState, PlayersRelation, TableConfig, TablesRelation
from tests.utils import IntegrationHttpTestCase


class TestTablesController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_tables(self):
        table_1_id = 1
        table_2_id = 2
        config1 = TableConfig(4, 9, 1, 2, 10)
        config2 = TableConfig(8, 15, 1, 2, 10)
        await TablesRelation.create_table(
            table_1_id, 'table1', config1, ['2s', '3s', '4s'], [], [{'bets': {}}],
            "frodo", None, "pippin", False, ''
        )
        await TablesRelation.create_table(
            table_2_id, 'table2', config2, ['7c', '8s', '9h'], [], [{'bets': {}}],
            "gandalf", None, "bilbo", False, ''
        )
        timestamp = datetime.now()
        await PlayersRelation.add_player(table_1_id, 1, "frodo", 10, ['Ac', 'Ad'], 0, timestamp, PlayerState.PLAYING)
        await PlayersRelation.add_player(table_1_id, 2, "pippin", 10, ['Kc', 'Kd'], 0, timestamp, PlayerState.PLAYING)
        await PlayersRelation.add_player(table_2_id, 1, "gandalf", 10, ['Ac', 'Ad'], 0, timestamp, PlayerState.PLAYING)
        await PlayersRelation.add_player(table_2_id, 2, "bilbo", 10, ['Kc', 'Kd'], 0, timestamp, PlayerState.PLAYING)

    @gen_test
    async def test_tables_response(self):
        # pylint: disable=no-member
        await self.create_tables()
        response = await self.fetch_async('/tables')
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        response_data = json.loads(response_body)
        self.assertEqual(response_data.keys(), {'tables'})
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
