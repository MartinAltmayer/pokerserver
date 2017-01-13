from asyncio.tasks import gather

from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from pokerserver.database.tables import TableConfig
from tests.integration import IntegrationTestCase

TABLES = [
    {
        'table_id': 1,
        'name': 'table1',
        'config': TableConfig(4, 9, 12, 24, 10),
        'remaining_deck': ['2s', 'Jc', '4h'],
        'open_cards': [],
        'main_pot': 1000,
        'side_pots': [],
        'current_player': 'a',
        'current_player_token': None,
        'dealer': 'b',
        'is_closed': False,
        'joined_players': ['a', 'b', 'c', 'd']
    }, {
        'table_id': 2,
        'name': 'table2',
        'config': TableConfig(4, 9, 12, 24, 10),
        'remaining_deck': ['2s', 'Jc', '4h'],
        'open_cards': [],
        'main_pot': 1000,
        'side_pots': [],
        'current_player': 'e',
        'current_player_token': None,
        'dealer': 'f',
        'is_closed': False,
        'joined_players': ['e', 'f', 'g', 'h']
    }, {
        'table_id': 3,
        'name': 'empty table',
        'config': TableConfig(4, 9, 12, 24, 10),
        'remaining_deck': ['2s', 'Jc', '4h'],
        'open_cards': [],
        'main_pot': 1000,
        'side_pots': [],
        'current_player': None,
        'current_player_token': None,
        'dealer': None,
        'is_closed': False,
        'joined_players': []
    }
]


class TestTablesRelation(IntegrationTestCase):
    @gen_test
    async def test_create_table(self):
        config = TableConfig(4, 30, 12, 24, 10)
        await TablesRelation.create_table(42, 'Game of Thrones', config, ['2s', 'Jc', '4h'], [], 1000, [],
                                          "Eddard", "123", "John", False, '')
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
                'current_player_token': "123",
                'dealer': 'John',
                'is_closed': False,
                'joined_players': []
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
    async def test_set_dealer(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_dealer(table_data['table_id'], 'Donald')

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('Donald', table['dealer'])

    @gen_test
    async def test_set_dealer_to_none(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_dealer(table_data['table_id'], None)

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertIsNone(table['dealer'])

    @gen_test
    async def test_set_current_player(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_current_player(table_data['table_id'], 'Jack', 'Jack\'s token')

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('Jack', table['current_player'])
        self.assertEqual('Jack\'s token', table['current_player_token'])

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

    @gen_test
    async def test_set_pot(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)
        amount = table_data['main_pot'] + 10

        await TablesRelation.set_pot(table_data['table_id'], amount)

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual(amount, table['main_pot'])

    @gen_test
    async def test_add_joined_player(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)
        joined_players = table_data['joined_players']
        assert joined_players

        await TablesRelation.add_joined_player(table_data['table_id'], 'xyzabc')

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual(joined_players + ['xyzabc'], table['joined_players'])


class TestCheckAndUnsetCurrentPlayer(IntegrationTestCase):
    async def async_setup(self):
        table_data = TABLES[0]
        table_id = table_data['table_id']
        await TablesRelation.create_table(**table_data)
        await TablesRelation.set_current_player(table_id, 'Scrooge', 'lotsofmoney')
        return table_id

    @gen_test
    async def test_success(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Scrooge')
        self.assertTrue(result)

        table = await TablesRelation.load_table_by_id(table_id)
        self.assertIsNone(table['current_player'])
        self.assertIsNone(table['current_player_token'])

    @gen_test
    async def test_success_with_token(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Scrooge', 'lotsofmoney')
        self.assertTrue(result)

        table = await TablesRelation.load_table_by_id(table_id)
        self.assertIsNone(table['current_player'])
        self.assertIsNone(table['current_player_token'])

    @gen_test
    async def test_wrong_player(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Dagobert')
        self.assertFalse(result)

    @gen_test
    async def test_wrong_token(self):
        table_id = await self.async_setup()
        result = await TablesRelation.check_and_unset_current_player(table_id, 'Scrooge', 'nomoney')
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

    @gen_test
    async def test_close_table(self):
        table_id = await self.async_setup()
        await TablesRelation.close_table(table_id)
        table = await TablesRelation.load_table_by_id(table_id)
        self.assertTrue(table['is_closed'])
