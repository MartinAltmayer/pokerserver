from unittest.mock import patch, call

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.database.database import Database
from pokerserver.models.card import get_all_cards
from pokerserver.models.player import Player
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import return_done_future, IntegrationTestCase, create_table


class TestTable(AsyncTestCase):
    @patch('pokerserver.database.players.PlayersRelation.load_by_table_id')
    @patch('pokerserver.database.tables.TablesRelation.load_all')
    @patch('pokerserver.database.tables.TablesRelation.create_table', side_effect=return_done_future())
    @gen_test
    async def test_create_tables(self, create_table, load_all_tables, load_player_by_table_id):
        max_player_count = 2
        small_blind = 13
        big_blind = 14
        players = ['Percival', 'Tristan', 'Lancelot', 'Arthur']
        existing_table_names = ['Table1', 'Table3', 'SomeName']
        existing_players = [
            {
                'table_id': table_id,
                'position': position,
                'name': name,
                'balance': position * 1000,
                'cards': 'AcAd',
                'bet': position * 500
            }
            for position, name in enumerate(players)
            for table_id in enumerate(existing_table_names)
        ]
        existing_tables = [
            {
                'table_id': table_id,
                'name': name,
                'max_player_count': 10,
                'remaining_deck': 'so many cards',
                'small_blind': 12,
                'big_blind': 24,
                'open_cards': 'turn',
                'main_pot': 3000,
                'side_pots': '',
                'current_player': 'Arthur',
                'dealer': 'Percival',
                'small_blind_player': 'Tristan',
                'big_blind_player': 'Lancelot',
                'is_closed': False
            }
            for table_id, name in enumerate(existing_table_names)
        ]
        load_player_by_table_id.side_effect = return_done_future(existing_players)
        load_all_tables.side_effect = return_done_future(existing_tables)

        await Table.create_tables(2, max_player_count, small_blind, big_blind)
        create_table.assert_has_calls([
            call(3, 'Table2', max_player_count, '', small_blind, big_blind, '', 0, '', None, None, None, None, False),
            call(4, 'Table4', max_player_count, '', small_blind, big_blind, '', 0, '', None, None, None, None, False)
        ])


class TestJoin(IntegrationTestCase):
    async def async_setup(self):
        self.player_name = 'player'
        await Table.create_tables(1, max_player_count=2, small_blind=1, big_blind=2)
        tables = await Table.load_all()
        self.table = tables[0]

    async def check_players(self, expected_players):
        table = await Table.load_by_name(self.table.name)
        actual_players = {player.position: player.name for player in table.players}
        self.assertEqual(expected_players, actual_players)

    @gen_test
    async def test_join(self):
        start_balance = 13
        await self.async_setup()
        await self.table.join(self.player_name, 1, start_balance)
        await self.check_players({1: self.player_name})
        self.assertEqual(self.player_name, self.table.players[0].name)
        self.assertEqual(1, self.table.players[0].position)
        self.assertEqual(start_balance, self.table.players[0].balance)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET is_closed = 1 WHERE table_id = ?", self.table.table_id)
        table = await Table.load_by_name(self.table.name)
        with self.assertRaises(ValueError):
            await table.join(self.player_name, 1, 0)
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.table.join(self.player_name, 0, 0)
        with self.assertRaises(ValueError):
            await self.table.join(self.player_name, 3, 0)
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await Table.join(self.table, self.player_name, 1, 0)
        with self.assertRaises(ValueError):
            await self.table.join(self.player_name + '2', 1, 0)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined(self):
        await self.async_setup()
        await Table.join(self.table, self.player_name, 1, 0)
        with self.assertRaises(ValueError):
            await self.table.join(self.player_name, 2, 0)
        await self.check_players({1: self.player_name})


class TestStartRound(IntegrationTestCase):
    @staticmethod
    def create_table(positions):
        table_id = 1
        players = [Player(table_id, position, name, 0, '', 0) for position, name in positions.items()]
        return Table(table_id, name='a table', max_player_count=10, players=players, small_blind=1, big_blind=2)

    def check_blind_players(self, players, small_blind, big_blind, start):
        self.assertEqual(players[0], small_blind.name)
        self.assertEqual(players[1], big_blind.name)
        self.assertEqual(players[2], start.name)

    def test_find_blind_players(self):
        table = self.create_table({1: 'a', 2: 'b', 3: 'c', 5: 'd'})
        small_blind, big_blind, start = table.find_blind_players(table.get_player_at(1))
        self.check_blind_players('bcd', small_blind, big_blind, start)

        small_blind, big_blind, start = table.find_blind_players(table.get_player_at(2))
        self.check_blind_players('cda', small_blind, big_blind, start)

    def test_find_blind_players_heads_up(self):
        table = self.create_table({1: 'a', 4: 'b'})
        small_blind, big_blind, start = table.find_blind_players(table.get_player_at(1))
        self.check_blind_players('abb', small_blind, big_blind, start)

        small_blind, big_blind, start = table.find_blind_players(table.get_player_at(4))
        self.check_blind_players('baa', small_blind, big_blind, start)

    def test_player_left_of(self):
        table = self.create_table({1: 'a', 2: 'b', 5: 'c'})
        for position, left_player_name in zip([1, 2, 5], 'bca'):
            player = table.get_player_at(position)
            self.assertEqual(left_player_name, table.player_left_of(player).name)

    @patch('random.shuffle')
    @gen_test
    async def test_distribute_cards(self, shuffle_mock):
        cards = get_all_cards()
        shuffle_mock.return_value = reversed(cards)
        table = await create_table(players={1: 'a', 2: 'b', 5: 'c'})

        await table.distribute_cards()

        table = await Table.load_by_name(table.name)
        self.assertCountEqual(cards[-2:], table.players[0].cards)
        self.assertCountEqual(cards[-4:-2], table.players[1].cards)
        self.assertCountEqual(cards[-6:-4], table.players[2].cards)
        self.assertCountEqual(cards[:-6], table.remaining_deck)

    @patch('random.choice')
    @gen_test
    async def test_start(self, choice_mock):
        table = await create_table(players={1: 'a', 2: 'b', 3: 'c'}, initial_balance=10)
        choice_mock.return_value = table.get_player_at(2)

        await table.start()

        table = await Table.load_by_name(table.name)
        self.assertEqual(table.get_player_at(2), table.dealer)
        self.assertEqual(table.get_player_at(3), table.small_blind_player)
        self.assertEqual(table.get_player_at(1), table.big_blind_player)
        self.assertEqual(table.get_player_at(2), table.current_player)
        self.assertEqual(10, table.dealer.balance)
        self.assertEqual(9, table.small_blind_player.balance)
        self.assertEqual(8, table.big_blind_player.balance)
        for player in table.players:
            self.assertEqual(2, len(player.cards))
        self.assertEqual(46, len(table.remaining_deck))
        self.assertEqual([], table.open_cards)
