from unittest import TestCase
from unittest.mock import Mock, patch

from nose.tools import assert_equal
from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import PlayerState, TableConfig
from pokerserver.database import TableState
from pokerserver.models import Player, Pot, Table
from tests.utils import return_done_future


class TestTable(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.players = [
            Mock(
                position=position,
                balance=balance,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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
            'state': TableState.WAITING_FOR_PLAYERS.value,
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

    @gen_test()
    async def test_has_all_in_players(self):
        pot = Pot(bets={1: 10})
        self.assertFalse(self.table.has_all_in_players(pot, 2))

        self.players[0].is_all_in.return_value = True
        self.assertTrue(self.table.has_all_in_players(pot, 2))
        self.assertFalse(self.table.has_all_in_players(pot, 1))

    @patch('pokerserver.models.table.Table.load_all')
    @patch('pokerserver.models.table.Table.create_tables', side_effect=return_done_future())
    @gen_test
    async def test_ensure_free_tables(self, create_tables, load_all):
        config = TableConfig(
            min_player_count=2, max_player_count=4, small_blind=12, big_blind=24, start_balance=10)
        existing_tables = [Table(i, 'name', config) for i in range(5)]
        load_all.side_effect = return_done_future(existing_tables)

        await Table.ensure_free_tables(10, config)

        create_tables.assert_called_once_with(5, config)


class TestPot(TestCase):
    def setUp(self):
        self.pot = Pot(bets={1: 1, 2: 2, 3: 0})

    def test_amount(self):
        self.assertEqual(3, self.pot.amount)

    def test_positions(self):
        self.assertEqual({1, 2, 3}, self.pot.positions)

    def test_max_bet(self):
        self.assertEqual(2, self.pot.max_bet)

    def test_bet(self):
        self.assertEqual(1, self.pot.bet(1))
        self.assertEqual(2, self.pot.bet(2))
        self.assertEqual(0, self.pot.bet(3))

    def test_add_bet(self):
        self.pot.add_bet(4, 10)
        self.assertEqual({1: 1, 2: 2, 3: 0, 4: 10}, self.pot.bets)

        self.pot.add_bet(1, 9)
        self.assertEqual({1: 10, 2: 2, 3: 0, 4: 10}, self.pot.bets)

    def test_split(self):
        new_pot = self.pot.split(1)

        self.assertEqual({1: 1, 2: 1, 3: 0}, self.pot.bets)
        self.assertEqual({2: 1}, new_pot.bets)

    def test_to_dict(self):
        self.assertEqual({'bets': {1: 1, 2: 2, 3: 0}}, self.pot.to_dict())
