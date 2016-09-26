from asyncio.tasks import gather
from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from pokerserver.database.tables import TableConfig
from tests.integration.utils.integration_test import IntegrationTestCase

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
        'dealer': 'b',
        'small_blind_player': 'c',
        'big_blind_player': 'd',
        'highest_bet_player': 'e',
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
        'dealer': 'f',
        'small_blind_player': 'g',
        'big_blind_player': 'h',
        'highest_bet_player': None,
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
        'dealer': None,
        'small_blind_player': None,
        'big_blind_player': None,
        'highest_bet_player': None,
        'is_closed': False,
        'joined_players': []
    }
]


class TestTablesRelation(IntegrationTestCase):
    @gen_test
    async def test_create_table(self):
        config = TableConfig(4, 30, 12, 24, 10)
        await TablesRelation.create_table(42, 'Game of Thrones', config, ['2s', 'Jc', '4h'], [], 1000, [],
                                          "Eddard", "John", "Arya", "Bran", None, False, '')
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
                'highest_bet_player': None,
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
    async def test_set_special_players(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_special_players(
            table_data['table_id'],
            dealer='Donald',
            small_blind_player='Huey',
            big_blind_player='Dewey',
            current_player='Louie',
            highest_bet_player='Scrooge'
        )

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('Donald', table['dealer'])
        self.assertEqual('Huey', table['small_blind_player'])
        self.assertEqual('Dewey', table['big_blind_player'])
        self.assertEqual('Louie', table['current_player'])
        self.assertEqual('Scrooge', table['highest_bet_player'])

    @gen_test
    async def test_set_special_players_none(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_special_players(
            table_data['table_id'],
            dealer=None,
            small_blind_player=None,
            big_blind_player=None,
            current_player=None,
            highest_bet_player=None
        )

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertIsNone(table['dealer'])
        self.assertIsNone(table['small_blind_player'])
        self.assertIsNone(table['big_blind_player'])
        self.assertIsNone(table['current_player'])
        self.assertIsNone(table['highest_bet_player'])

    @gen_test
    async def test_set_special_players_partial(self):
        table_data = TABLES[0]
        await TablesRelation.create_table(**table_data)

        await TablesRelation.set_special_players(
            table_data['table_id'],
            dealer='John'
        )

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual('John', table['dealer'])
        for key in ['small_blind_player', 'big_blind_player', 'current_player', 'highest_bet_player']:
            self.assertEqual(table_data[key], table[key])

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
        assert len(joined_players) > 0

        await TablesRelation.add_joined_player(table_data['table_id'], 'xyzabc')

        table = await TablesRelation.load_table_by_name(table_data['name'])
        self.assertEqual(joined_players + ['xyzabc'], table['joined_players'])


class TestCheckAndUnsetCurrentPlayer(IntegrationTestCase):
    async def async_setup(self):
        table_data = TABLES[0]
        table_id = table_data['table_id']
        await TablesRelation.create_table(**table_data)
        await TablesRelation.set_special_players(table_id, current_player='Scrooge')
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

    @gen_test
    async def test_close_table(self):
        table_id = await self.async_setup()
        await TablesRelation.close_table(table_id)
        table = await TablesRelation.load_table_by_id(table_id)
        self.assertTrue(table['is_closed'])
