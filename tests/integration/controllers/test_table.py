from uuid import uuid4
from unittest.mock import patch, Mock
from http import HTTPStatus
from tornado.testing import gen_test

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future


class TestJoinController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        await Table.create_tables(1, max_player_count=2, small_blind=1, big_blind=2)
        tables = await Table.load_all()
        self.table_name = tables[0].name

    async def check_players(self, expected_players):
        table = await Table.load_by_name(self.table_name)
        actual_players = {player.position: player.name for player in table.players}
        self.assertEqual(expected_players, actual_players)

    @gen_test
    async def test_join(self):
        await self.async_setup()
        with patch('pokerserver.models.table.Table.load_by_name') as load_mock:
            table_mock = Mock()
            table_mock.join.side_effect = return_done_future()
            load_mock.side_effect = return_done_future(table_mock)

            response = await self.fetch_async('/table/{}/join?position=1&uuid={}'.format(self.table_name, self.uuid))

            self.assertEqual(response.code, HTTPStatus.OK.value)
            load_mock.assert_called_once_with(self.table_name)
            table_mock.join.assert_called_once_with(self.player_name, 1, self.args.start_balance)
