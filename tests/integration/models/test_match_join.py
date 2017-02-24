from asyncio.tasks import gather
from unittest.mock import Mock

from tornado.testing import gen_test

from pokerserver.database import Database, TableConfig, TablesRelation
from pokerserver.models import (Match, PositionOccupiedError, Table)
from tests.utils import IntegrationTestCase, return_done_future


class TestJoin(IntegrationTestCase):
    async def async_setup(self, table_count=1, start_balance=10):
        self.player_name = 'player'
        config = TableConfig(min_player_count=2, max_player_count=2, small_blind=1, big_blind=2,
                             start_balance=start_balance)
        await Table.create_tables(table_count, config)
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
        await self.async_setup(start_balance=13)

        await self.match.join(self.player_name, 1)

        await self.check_players({1: self.player_name})
        self.assertEqual(self.player_name, self.table.players[0].name)
        self.assertEqual(1, self.table.players[0].position)
        self.assertEqual(13, self.table.players[0].balance)

    @gen_test
    async def test_joined_players(self):
        await self.async_setup(start_balance=10)
        await self.match.join(self.player_name, 1)

        table = await Table.load_by_name(self.table.name)
        self.assertEqual([self.player_name], table.joined_players)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET is_closed = 1 WHERE table_id = ?", self.table.table_id)
        await self.load_match()

        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 1)
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 3)
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(PositionOccupiedError):
            await self.match.join(self.player_name + '2', 1)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_at_table(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined_in_the_past(self):
        await self.async_setup()
        await TablesRelation.add_joined_player(self.table.table_id, self.player_name)
        await self.load_match()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)

    @gen_test
    async def test_join_and_start(self):
        await self.async_setup()
        self.match.start = Mock(side_effect=return_done_future())
        await self.match.join(self.player_name, 1)
        self.match.start.assert_not_called()
        await self.match.join(self.player_name + ' II.', 2)
        self.match.start.assert_called_once_with()

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
