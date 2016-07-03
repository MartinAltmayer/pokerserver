from uuid import uuid4
from unittest.mock import patch, Mock
from http import HTTPStatus
from tornado.testing import gen_test

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future, create_table


class TestJoinController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

    async def check_players(self, expected_players):
        table = await Table.load_by_name(self.table_name)
        actual_players = {player.position: player.name for player in table.players}
        self.assertEqual(expected_players, actual_players)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_join(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.join.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/join?position=1&uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.join.assert_called_once_with(self.player_name, 1, self.args.start_balance)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_join_and_start(self, load_mock):
        await self.async_setup()
        self.args.min_player_count = 2
        match_mock = Mock()
        match_mock.table.players = ['some player', 'another player']
        match_mock.join.side_effect = return_done_future()
        match_mock.start.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async(
            '/table/{}/join?position=1&uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.join.assert_called_once_with(self.player_name, 1, self.args.start_balance)
        match_mock.start.assert_called_once_with()
