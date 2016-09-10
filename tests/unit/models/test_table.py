from unittest.mock import patch

from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import TableConfig
from pokerserver.models import Table, Player
from tests.integration.utils.integration_test import return_done_future


class TestTable(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.table = Table(
            42,
            "Table1",
            TableConfig(min_player_count=4, max_player_count=8, small_blind=1, big_blind=10)
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
            'main_pot': 0,
            'open_cards': [],
            'players': [],
            'side_pots': [],
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
            'main_pot': 0,
            'open_cards': [],
            'players': [],
            'side_pots': [],
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
            'main_pot': 0,
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'has_folded': False
                }
                for i in range(7)
            ],
            'side_pots': [],
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
            'main_pot': 0,
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'has_folded': False
                }
                for i in range(7)
            ],
            'side_pots': [],
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
            'main_pot': 0,
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'has_folded': False
                }
                for i in range(8)
            ],
            'side_pots': [],
            'small_blind': 1
        })

    def test_to_dict_with_full_table_and_authorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(8)]
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'big_blind': 10,
            'can_join': False,
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'round': 'preflop',
            'main_pot': 0,
            'open_cards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0,
                    'has_folded': False
                }
                for i in range(8)
            ],
            'side_pots': [],
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
