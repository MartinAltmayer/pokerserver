from asyncio.tasks import gather

from tornado.testing import gen_test

from pokerserver.database import Database, PlayerState, TableConfig, TableState, TablesRelation
from pokerserver.models import (Match, PositionOccupiedError, Table)
from tests.utils import IntegrationTestCase


class TestJoin(IntegrationTestCase):
    async def async_setup(self, table_count=1, start_balance=10):
        self.player_name = 'player'
        config = TableConfig(min_player_count=2, max_player_count=4, small_blind=1, big_blind=2,
                             start_balance=start_balance)
        await Table.create_tables(table_count, config)
        await self.load_match_and_table()

    async def load_match_and_table(self):
        tables = await Table.load_all()
        self.table = tables[0]
        self.match = Match(self.table)

    async def check_players(self, expected_players):
        actual_players = {player.position: player.name for player in self.table.players}
        self.assertEqual(expected_players, actual_players)

    @gen_test
    async def test_join(self):
        await self.async_setup(start_balance=13)

        await self.match.join(self.player_name, 1)

        await self.load_match_and_table()
        await self.check_players({1: self.player_name})
        player = self.table.players[0]
        self.assertEqual(1, player.position)
        self.assertEqual(13, player.balance)
        self.assertEqual(PlayerState.SITTING_OUT, player.state)

    @gen_test
    async def test_joined_players(self):
        await self.async_setup(start_balance=10)
        await self.match.join(self.player_name, 1)

        await self.load_match_and_table()
        self.assertEqual([self.player_name], self.table.joined_players)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET state = 'closed' WHERE table_id = ?", self.table.table_id)
        await self.load_match_and_table()

        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 1)
        await self.load_match_and_table()
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 5)
        await self.load_match_and_table()
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(PositionOccupiedError):
            await self.match.join(self.player_name + '2', 1)
        await self.load_match_and_table()
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_at_table(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)
        await self.load_match_and_table()
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined_in_the_past(self):
        await self.async_setup()
        await TablesRelation.add_joined_player(self.table.table_id, self.player_name)
        await self.load_match_and_table()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)

    @gen_test
    async def test_join_and_start(self):
        await self.async_setup()

        await self.match.join(self.player_name, 1)

        await self.load_match_and_table()
        self.assertEqual(TableState.WAITING_FOR_PLAYERS, self.table.state)
        self.assertIsNone(self.table.dealer)
        self.assertEqual(PlayerState.SITTING_OUT, self.table.players[0].state)

        await self.match.join(self.player_name + ' II.', 2)

        await self.load_match_and_table()
        self.assertIsNotNone(self.table.dealer)
        self.assertEqual(TableState.RUNNING_GAME, self.table.state)
        self.assertEqual(PlayerState.PLAYING, self.table.players[0].state)
        self.assertEqual(PlayerState.PLAYING, self.table.players[1].state)

        await self.match.join(self.player_name + ' III.', 3)
        self.assertIsNotNone(self.table.dealer)
        self.assertEqual(PlayerState.PLAYING, self.table.players[0].state)
        self.assertEqual(PlayerState.PLAYING, self.table.players[1].state)
        self.assertEqual(PlayerState.SITTING_OUT, self.table.players[2].state)

    @gen_test
    async def test_join_two_tables(self):
        await self.async_setup(table_count=2)
        tables = await Table.load_all()
        self.assertEqual(len(tables), 2)
        for table in tables:
            match = Match(table)
            await match.join(self.player_name, 1)

    @gen_test
    async def test_join_concurrent(self):
        await self.async_setup()
        with self.assertRaises(PositionOccupiedError):
            await gather(
                self.match.join(self.player_name, 1),
                self.match.join('other player', 1),
                loop=self.get_asyncio_loop()
            )
