from unittest.mock import Mock, patch

from nose.tools import assert_equal
from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import PlayerState, TableConfig
from pokerserver.models import Player, Table
from tests.utils import return_done_future


class TestTable(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.players = [
            Mock(
                position=position,
                is_all_in=Mock(return_value=False),
                to_dict=Mock(return_value={})
            )
            for position, balance in [(1, 10), (2, 10), (5, 10)]
        ]
        self.table = Table(
            42,
            "Table1",
            TableConfig(min_player_count=4, max_player_count=8, small_blind=1, big_blind=10, start_balance=10),
            players=self.players
        )

    def test_to_dict_without_players_and_unauthorized(self):
        result = self.table.to_dict(None)
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': True,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [{}, {}, {}],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    def test_to_dict_without_players_and_authorized(self):
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': True,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [{}, {}, {}],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    def test_to_dict_with_players_and_unauthorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(7)]
        result = self.table.to_dict(None)
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': True,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'state': PlayerState.PLAYING.value
                }
                for i in range(7)
            ],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    def test_to_dict_with_players_and_authorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(7)]
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': False,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'state': PlayerState.PLAYING.value
                }
                for i in range(7)
            ],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    def test_to_dict_with_full_table_and_unauthorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(8)]
        result = self.table.to_dict(None)
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': False,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'state': PlayerState.PLAYING.value
                }
                for i in range(8)
            ],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    def test_to_dict_with_full_table_and_authorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(8)]
        result = self.table.to_dict("Player1")
        assert_equal(result, {
            'big_blind': 10,
            'can_join': False,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'state': PlayerState.PLAYING.value
                }
                for i in range(8)
            ],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'small_blind': 1
        })

    @patch('pokerserver.database.tables.TablesRelation.set_cards', side_effect=return_done_future())
    @gen_test
    async def test_draw_cards(self, set_cards_mock):
        self.table.remaining_deck = ['8c', '3s', '2h', '3h', '4h']

        await self.table.draw_cards(3)
        self.assertEqual(['8c', '3s'], self.table.remaining_deck)
        self.assertEqual(['2h', '3h', '4h'], self.table.open_cards)

        set_cards_mock.assert_called_once_with(self.table.table_id, ['8c', '3s'], ['2h', '3h', '4h'])

    @patch('pokerserver.database.tables.TablesRelation.set_pots', side_effect=return_done_future())
    @gen_test()
    async def test_clear_pots(self, mock_set_pots):
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

        await self.table.increase_pot(self.players[0].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(10, self.table.pots[0].amount)
        mock_set_pots.reset_mock()

        await self.table.clear_pots()
        mock_set_pots.assert_called_once_with(42, [{'bets': {}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

    @patch('pokerserver.database.tables.TablesRelation.set_pots', side_effect=return_done_future())
    @gen_test()
    async def test_increase_pot(self, mock_set_pots):
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

        await self.table.increase_pot(self.players[0].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(10, self.table.pots[0].amount)
        mock_set_pots.reset_mock()

        await self.table.increase_pot(self.players[1].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10, 2: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(20, self.table.pots[0].amount)

    @patch('pokerserver.database.tables.TablesRelation.set_pots', side_effect=return_done_future())
    @gen_test()
    async def test_increase_pot_smaller_second_bet(self, mock_set_pots):
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

        await self.table.increase_pot(self.players[0].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(10, self.table.pots[0].amount)
        mock_set_pots.reset_mock()

        await self.table.increase_pot(self.players[1].position, 8)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 8, 2: 8}}, {'bets': {1: 2}}])
        self.assertEqual(2, len(self.table.pots))
        self.assertEqual(16, self.table.pots[0].amount)
        self.assertEqual(2, self.table.pots[1].amount)

    @patch('pokerserver.database.tables.TablesRelation.set_pots', side_effect=return_done_future())
    @gen_test()
    async def test_increase_pot_larger_second_bet(self, mock_set_pots):
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

        await self.table.increase_pot(self.players[0].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(10, self.table.pots[0].amount)
        mock_set_pots.reset_mock()

        await self.table.increase_pot(self.players[1].position, 12)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10, 2: 12}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(22, self.table.pots[0].amount)

    @patch('pokerserver.database.tables.TablesRelation.set_pots', side_effect=return_done_future())
    @gen_test()
    async def test_increase_pot_all_in(self, mock_set_pots):
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(0, self.table.pots[0].amount)

        await self.table.increase_pot(self.players[0].position, 10)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10}}])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(10, self.table.pots[0].amount)
        self.players[0].is_all_in.return_value = True
        mock_set_pots.reset_mock()

        await self.table.increase_pot(self.players[1].position, 12)
        mock_set_pots.assert_called_once_with(42, [{'bets': {1: 10, 2: 10}}, {'bets': {2: 2}}])
        self.assertEqual(2, len(self.table.pots))
        self.assertEqual(20, self.table.pots[0].amount)
        self.assertEqual(2, self.table.pots[1].amount)
