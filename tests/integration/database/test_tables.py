from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from tests.integration.utils.integration_test import IntegrationTestCase


class TestTablesRelation(IntegrationTestCase):
    TABLES = [
        {
            'table_id': 1,
            'name': 'table1',
            'max_player_count': 9,
            'remaining_deck': ['2s', 'Jc', '4h'],
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': [],
            'main_pot': 1000,
            'side_pots': [],
            'current_player': 'a',
            'dealer': 'b',
            'small_blind_player': 'c',
            'big_blind_player': 'd',
            'is_closed': False
        }, {
            'table_id': 2,
            'name': 'table2',
            'max_player_count': 15,
            'remaining_deck': ['2s', 'Jc', '4h'],
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': [],
            'main_pot': 1000,
            'side_pots': [],
            'current_player': 'e',
            'dealer': 'f',
            'small_blind_player': 'g',
            'big_blind_player': 'h',
            'is_closed': False
        }, {
            'table_id': 3,
            'name': 'empty table',
            'max_player_count': 2,
            'remaining_deck': ['2s', 'Jc', '4h'],
            'small_blind': 12,
            'big_blind': 24,
            'open_cards': [],
            'main_pot': 1000,
            'side_pots': [],
            'current_player': None,
            'dealer': None,
            'small_blind_player': None,
            'big_blind_player': None,
            'is_closed': False
        }
    ]

    @gen_test
    async def test_create_table(self):
        await TablesRelation.create_table(42, 'Game of Thrones', 30, ['2s', 'Jc', '4h'], 12, 24, [], 1000, [],
                                          "Eddard", "John", "Arya", "Bran", False)
        tables = await TablesRelation.load_all()
        self.assertEqual(
            tables,
            [{
                'table_id': 42,
                'name': 'Game of Thrones',
                'max_player_count': 30,
                'remaining_deck': ['2s', 'Jc', '4h'],
                'small_blind': 12,
                'big_blind': 24,
                'open_cards': [],
                'main_pot': 1000,
                'side_pots': [],
                'current_player': 'Eddard',
                'dealer': 'John',
                'small_blind_player': 'Arya',
                'big_blind_player': 'Bran',
                'is_closed': False
            }]
        )

    @gen_test
    async def test_load_table_by_name(self):
        for table in self.TABLES:
            await TablesRelation.create_table(**table)
        table2 = await TablesRelation.load_table_by_name('table2')
        self.assertEqual(self.TABLES[1], table2)

    @gen_test
    async def test_set_special_players(self):
        table_data = self.TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_special_players(
            table_data['table_id'],
            dealer='Donald',
            small_blind_player='Huey',
            big_blind_player='Dewey',
            current_player='Louie'
        )

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('Donald', table['dealer'])
        self.assertEqual('Huey', table['small_blind_player'])
        self.assertEqual('Dewey', table['big_blind_player'])
        self.assertEqual('Louie', table['current_player'])

    @gen_test
    async def test_set_cards(self):
        table_data = self.TABLES[0]
        await TablesRelation.create_table(**table_data)
        remaining_deck = ['8c', '3s', '2h']
        open_cards = ['9h', '3h']

        await TablesRelation.set_cards(table_data['table_id'], remaining_deck, open_cards)

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual(remaining_deck, table['remaining_deck'])
        self.assertEqual(open_cards, table['open_cards'])
