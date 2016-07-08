from asyncio.tasks import gather
from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from pokerserver.database.tables import TableConfig
from tests.integration.utils.integration_test import IntegrationTestCase

TABLES = [
    {
        'table_id': 1,
        'name': 'table1',
        'config': TableConfig(4, 9, 12, 24),
        'remaining_deck': ['2s', 'Jc', '4h'],
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
        'config': TableConfig(4, 9, 12, 24),
        'remaining_deck': ['2s', 'Jc', '4h'],
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
        'config': TableConfig(4, 9, 12, 24),
        'remaining_deck': ['2s', 'Jc', '4h'],
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


class TestTablesRelation(IntegrationTestCase):
    @gen_test
    async def test_create_table(self):
        config = TableConfig(4, 30, 12, 24)
        await TablesRelation.create_table(42, 'Game of Thrones', config, ['2s', 'Jc', '4h'], [], 1000, [],
                                          "Eddard", "John", "Arya", "Bran", False)
        tables = await TablesRelation.load_all()
        self.assertEqual(
            tables,
            [{
                'table_id': 42,
                'name': 'Game of Thrones',
                'config': config,
                'remaining_deck': ['2s', 'Jc', '4h'],
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
    async def test_load_table_by_id(self):
        for table in TABLES:
            await TablesRelation.create_table(**table)
        table2 = await TablesRelation.load_table_by_id(2)
        self.assertEqual(TABLES[1], table2)

    @gen_test
    async def test_load_table_by_name(self):
        for table in TABLES:
            await TablesRelation.create_table(**table)
        table2 = await TablesRelation.load_table_by_name('table2')
        self.assertEqual(TABLES[1], table2)

    @gen_test
    async def test_set_special_players(self):
        table_data = TABLES[0]
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
    async def test_set_current_player(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_current_player(table_data['table_id'], 'Dagobert')

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('Dagobert', table['current_player'])

    @gen_test
    async def test_set_cards(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)
        remaining_deck = ['8c', '3s', '2h']
        open_cards = ['9h', '3h']

        await TablesRelation.set_cards(table_data['table_id'], remaining_deck, open_cards)

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual(remaining_deck, table['remaining_deck'])
        self.assertEqual(open_cards, table['open_cards'])


class TestCheckAndUnsetCurrentPlayer(IntegrationTestCase):
    async def async_setup(self):
        table_data = TABLES[0]
        table_id = table_data['table_id']
        await TablesRelation.create_table(**table_data)
        await TablesRelation.set_current_player(table_id, 'Scrooge')
        return table_id

    @gen_test
    async def test_success(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Scrooge')
        self.assertTrue(result)

        table = await TablesRelation.load_table_by_id(table_id)
        self.assertIsNone(table['current_player'])

    @gen_test
    async def test_wrong_player(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Dagobert')
        self.assertFalse(result)

    @gen_test
    async def test_concurrent(self):
        table_id = await self.async_setup()
        results = await gather(
            TablesRelation.check_and_unset_current_player(table_id, 'Scrooge'),
            TablesRelation.check_and_unset_current_player(table_id, 'Scrooge'),
            loop=self.get_asyncio_loop()
        )
        self.assertEqual({True, False}, set(results))
