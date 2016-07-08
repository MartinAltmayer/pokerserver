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
            'bigBlind': 10,
            'canJoin': True,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [],
            'sidePots': [],
            'smallBlind': 1
        })

    def test_to_dict_without_players_and_authorized(self):
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'bigBlind': 10,
            'canJoin': True,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [],
            'sidePots': [],
            'smallBlind': 1
        })

    def test_to_dict_with_players_and_unauthorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(7)]
        result = self.table.to_dict(None)
        self.assertEqual(result, {
            'bigBlind': 10,
            'canJoin': True,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0
                }
                for i in range(7)
            ],
            'sidePots': [],
            'smallBlind': 1
        })

    def test_to_dict_with_players_and_authorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(7)]
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'bigBlind': 10,
            'canJoin': False,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0
                }
                for i in range(7)
            ],
            'sidePots': [],
            'smallBlind': 1
        })

    def test_to_dict_with_full_table_and_unauthorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(8)]
        result = self.table.to_dict(None)
        self.assertEqual(result, {
            'bigBlind': 10,
            'canJoin': False,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0
                }
                for i in range(8)
            ],
            'sidePots': [],
            'smallBlind': 1
        })

    def test_to_dict_with_full_table_and_authorized(self):
        self.table.players = [Player(42, i, "Player{}".format(i), 0, [], 0, None) for i in range(8)]
        result = self.table.to_dict("Player1")
        self.assertEqual(result, {
            'bigBlind': 10,
            'canJoin': False,
            'currentPlayer': None,
            'dealer': None,
            'isClosed': False,
            'mainPot': 0,
            'openCards': [],
            'players': [
                {
                    'table_id': 42,
                    'position': i,
                    'name': "Player{}".format(i),
                    'balance': 0,
                    'cards': [],
                    'bet': 0
                }
                for i in range(8)
            ],
            'sidePots': [],
            'smallBlind': 1
        })
