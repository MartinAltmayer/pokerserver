from http import HTTPStatus
from json import loads
from unittest.mock import patch, Mock
from uuid import uuid4

from tornado.testing import gen_test

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationHttpTestCase, return_done_future, create_table


class TestTableController(IntegrationHttpTestCase):
    async def async_setup(self):
        table = await create_table(players={1: 'a', 2: 'b', 5: 'c'})
        self.table_name = table.name

    @gen_test
    async def test_get(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}'.format(self.table_name))
        self.assertEqual(response.code, HTTPStatus.OK.value)
        table = loads(response.body.decode())
        self.assertEqual(table, {
            'bigBlind': 2,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [{
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'a',
                'bet': 0,
                'position': 1
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'b',
                'bet': 0,
                'position': 2
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'c',
                'bet': 0,
                'position': 5
            }],
            'sidePots': [],
            'smallBlind': 1
        })


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
