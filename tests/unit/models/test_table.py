from unittest import TestCase

from pokerserver.database import TableConfig
from pokerserver.models import Table, Player


class TestTable(TestCase):
    def setUp(self):
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
