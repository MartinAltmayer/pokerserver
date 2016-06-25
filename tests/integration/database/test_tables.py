from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from tests.integration.utils.integration_test import IntegrationTestCase


class TestTablesRelation(IntegrationTestCase):
    TABLES = [
        {
            'id': 1,
            'name': 'table1',
            'max_player_count': 9,
            'remaining_deck': 'so many cards',
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': 'turn',
            'main_pot': 1000,
            'side_pots': '',
            'current_player': 'a',
            'dealer': 'b',
            'small_blind_player': 'c',
            'big_blind_player': 'd',
            'is_closed': False
        }, {
            'id': 2,
            'name': 'table2',
            'max_player_count': 15,
            'remaining_deck': 'so many cards',
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': 'turn',
            'main_pot': 1000,
            'side_pots': '',
            'current_player': 'e',
            'dealer': 'f',
            'small_blind_player': 'g',
            'big_blind_player': 'h',
            'is_closed': False
        }, {
            'id': 3,
            'name': 'empty table',
            'max_player_count': 2,
            'remaining_deck': 'so many cards',
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': 'turn',
            'main_pot': 1000,
            'side_pots': '',
            'current_player': None,
            'dealer': None,
            'small_blind_player': None,
            'big_blind_player': None,
            'is_closed': False
        }
    ]

    @gen_test
    async def test_create_table(self):
        await TablesRelation.create_table(42, 'Round Table', 30, "so many cards", 12, 24, "turn", 1000, "", "Arthur",
                                          "Percival", "Tristan", "Lancelot", False)
        tables = await TablesRelation.load_all()
        self.assertEqual(
            tables,
            [{
                'id': 42,
                'name': 'Round Table',
                'max_player_count': 30,
                'remaining_deck': 'so many cards',
                'small_blind': 12,
                'big_blind': 24,
                'open_cards': 'turn',
                'main_pot': 1000,
                'side_pots': '',
                'current_player': 'Arthur',
                'dealer': 'Percival',
                'small_blind_player': 'Tristan',
                'big_blind_player': 'Lancelot',
                'is_closed': False
            }]
        )

    @gen_test
    async def test_load_table_by_name(self):
        for table in self.TABLES:
            await TablesRelation.create_table(**table)
        table2 = await TablesRelation.load_table_by_name('table2')
        self.assertEqual(self.TABLES[1], table2)
