from unittest.mock import patch, call

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.database.database import Database
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import return_done_future, IntegrationTestCase


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
