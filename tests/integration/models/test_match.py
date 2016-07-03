from unittest.mock import patch
from tornado.testing import gen_test

from pokerserver.database.database import Database
from pokerserver.database.tables import TableConfig
from pokerserver.models.card import get_all_cards
from pokerserver.models.match import Match
from pokerserver.models.player import Player
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import IntegrationTestCase, create_table


class TestJoin(IntegrationTestCase):
    async def async_setup(self):
        self.player_name = 'player'
        config = TableConfig(min_player_count=2, max_player_count=2, small_blind=1, big_blind=2)
        await Table.create_tables(1, config)
        await self.load_match()

    async def load_match(self):
        tables = await Table.load_all()
        self.table = tables[0]
        self.match = Match(self.table)

    async def check_players(self, expected_players):
        table = await Table.load_by_name(self.table.name)
        actual_players = {player.position: player.name for player in table.players}
        self.assertEqual(expected_players, actual_players)

    @gen_test
    async def test_join(self):
        start_balance = 13
        await self.async_setup()

        await self.match.join(self.player_name, 1, start_balance)

        await self.check_players({1: self.player_name})
        self.assertEqual(self.player_name, self.table.players[0].name)
        self.assertEqual(1, self.table.players[0].position)
        self.assertEqual(start_balance, self.table.players[0].balance)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET is_closed = 1 WHERE table_id = ?", self.table.table_id)
        await self.load_match()

        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 1, 0)
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 0, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 3, 0)
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name + '2', 1, 0)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2, 0)
        await self.check_players({1: self.player_name})


class TestStartRound(IntegrationTestCase):
    @staticmethod
    def create_match(positions):
        table_id = 1
        players = [Player(table_id, position, name, 0, '', 0) for position, name in positions.items()]
        config = TableConfig(min_player_count=2, max_player_count=10, small_blind=1, big_blind=2)
        return Match(Table(table_id, 'a table', config, players))

    def check_blind_players(self, players, small_blind, big_blind, start):
        self.assertEqual(players[0], small_blind.name)
        self.assertEqual(players[1], big_blind.name)
        self.assertEqual(players[2], start.name)

    def test_find_blind_players(self):
        match = self.create_match({1: 'a', 2: 'b', 3: 'c', 5: 'd'})
        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(1))
        self.check_blind_players('bcd', small_blind, big_blind, start)

        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(2))
        self.check_blind_players('cda', small_blind, big_blind, start)

    def test_find_blind_players_heads_up(self):
        match = self.create_match({1: 'a', 4: 'b'})
        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(1))
        self.check_blind_players('abb', small_blind, big_blind, start)

        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(4))
        self.check_blind_players('baa', small_blind, big_blind, start)

    @patch('random.shuffle')
    @gen_test
    async def test_distribute_cards(self, shuffle_mock):
        cards = get_all_cards()
        shuffle_mock.return_value = reversed(cards)
        table = await create_table(players={1: 'a', 2: 'b', 5: 'c'})
        match = Match(table)

        await match.distribute_cards()

        table = await Table.load_by_name(table.name)
        self.assertCountEqual(cards[-2:], table.players[0].cards)
        self.assertCountEqual(cards[-4:-2], table.players[1].cards)
        self.assertCountEqual(cards[-6:-4], table.players[2].cards)
        self.assertCountEqual(cards[:-6], table.remaining_deck)

    @patch('random.choice')
    @gen_test
    async def test_start(self, choice_mock):
        table = await create_table(players={1: 'a', 2: 'b', 3: 'c'}, initial_balance=10)
        match = Match(table)
        choice_mock.return_value = table.get_player_at(2)

        await match.start()

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
