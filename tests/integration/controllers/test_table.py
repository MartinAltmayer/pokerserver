from http import HTTPStatus
from json import loads
from unittest.mock import patch, Mock
from uuid import uuid4

from tornado.testing import gen_test

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models import Player, NotYourTurnError, PositionOccupiedError, InvalidTurnError
from tests.utils import IntegrationHttpTestCase, return_done_future, create_table


class TestTableController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.table_id = 1
        self.uuid = uuid4()
        self.uuid2 = uuid4()
        self.player_name = 'c'
        self.player_name2 = 'd'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        await UUIDsRelation.add_uuid(self.uuid2, self.player_name2)
        players = [
            Player(self.table_id, 1, 'a', 0, ['Ah', 'Ac'], 0),
            Player(self.table_id, 2, 'b', 0, ['Kh', 'Kc'], 0),
            Player(self.table_id, 5, 'c', 0, ['Qh', 'Qc'], 0)
        ]
        table = await create_table(table_id=self.table_id, players=players)
        self.table_name = table.name

    @gen_test
    async def test_get_for_player_at_table(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}?uuid={}'.format(self.table_name, self.uuid))
        self.assertEqual(response.code, HTTPStatus.OK.value)
        table = loads(response.body.decode())
        self.assertEqual(table, {
            'big_blind': 2,
            'can_join': False,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'main_pot': 0,
            'open_cards': [],
            'players': [{
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'a',
                'bet': 0,
                'position': 1,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'b',
                'bet': 0,
                'position': 2,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': ['Qh', 'Qc'],
                'name': 'c',
                'bet': 0,
                'position': 5,
                'has_folded': False
            }],
            'side_pots': [],
            'small_blind': 1
        })

    @gen_test
    async def test_get_for_player_not_at_table(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}?uuid={}'.format(self.table_name, self.uuid2))
        self.assertEqual(response.code, HTTPStatus.OK.value)
        table = loads(response.body.decode())
        self.assertEqual(table, {
            'big_blind': 2,
            'can_join': True,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'main_pot': 0,
            'open_cards': [],
            'players': [{
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'a',
                'bet': 0,
                'position': 1,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'b',
                'bet': 0,
                'position': 2,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'c',
                'bet': 0,
                'position': 5,
                'has_folded': False
            }],
            'side_pots': [],
            'small_blind': 1
        })

    @gen_test
    async def test_get_for_unauthorized_player(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}'.format(self.table_name))
        self.assertEqual(response.code, HTTPStatus.OK.value)
        table = loads(response.body.decode())
        self.assertEqual(table, {
            'big_blind': 2,
            'can_join': True,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'main_pot': 0,
            'open_cards': [],
            'players': [{
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'a',
                'bet': 0,
                'position': 1,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'b',
                'bet': 0,
                'position': 2,
                'has_folded': False
            }, {
                'table_id': 1,
                'balance': 0,
                'cards': [],
                'name': 'c',
                'bet': 0,
                'position': 5,
                'has_folded': False
            }],
            'side_pots': [],
            'small_blind': 1
        })


class TestJoinController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

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
        match_mock.join.assert_called_once_with(self.player_name, 1)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_join_occupied_position(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.join.side_effect = return_done_future(exception=PositionOccupiedError)
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/join?position=1&uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)

        self.assertEqual(response.code, HTTPStatus.CONFLICT.value)

    @gen_test
    async def test_join_missing_parameter(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}/join?uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)

    @gen_test
    async def test_join_invalid_parameter(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}/join?position=-1&uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)


class TestFoldController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_fold(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.fold.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/fold?uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.fold.assert_called_once_with(self.player_name)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_fold_invalid_turn(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.fold.side_effect = return_done_future(exception=NotYourTurnError)
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/fold?uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)

        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)


class TestCallController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_call(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.call.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/call?uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.call.assert_called_once_with(self.player_name)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_call_invalid_turn(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.call.side_effect = return_done_future(exception=NotYourTurnError)
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/call?uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)

        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)


class TestCheckController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_check(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.check.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/check?uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.check.assert_called_once_with(self.player_name)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_check_invalid_turn(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.check.side_effect = return_done_future(exception=InvalidTurnError)
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/check?uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)

        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)


class TestRaiseController(IntegrationHttpTestCase):
    async def async_setup(self):
        self.uuid = uuid4()
        self.player_name = 'player'
        await UUIDsRelation.add_uuid(self.uuid, self.player_name)
        table = await create_table(max_player_count=2)
        self.table_name = table.name

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_raise(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.raise_bet.side_effect = return_done_future()
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/raise?amount=17&uuid={}'.format(self.table_name, self.uuid))

        self.assertEqual(response.code, HTTPStatus.OK.value)
        load_mock.assert_called_once_with(self.table_name)
        match_mock.raise_bet.assert_called_once_with(self.player_name, 17)

    @patch('pokerserver.controllers.base.BaseController.load_match')
    @gen_test
    async def test_raise_invalid_turn(self, load_mock):
        await self.async_setup()
        match_mock = Mock()
        match_mock.table.players = []
        match_mock.raise_bet.side_effect = return_done_future(exception=NotYourTurnError)
        load_mock.side_effect = return_done_future(match_mock)

        response = await self.fetch_async('/table/{}/raise?amount=3&uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)

        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)

    @gen_test
    async def test_raise_missing_parameter(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}/raise?uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)

    @gen_test
    async def test_raise_invalid_parameter(self):
        await self.async_setup()
        response = await self.fetch_async('/table/{}/raise?amount=googol&uuid={}'.format(self.table_name, self.uuid),
                                          raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)
