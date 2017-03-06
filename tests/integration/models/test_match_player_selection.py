import asyncio
from unittest.mock import Mock, patch
from uuid import uuid4

from tornado.testing import gen_test

from pokerserver.configuration import ServerConfig
from pokerserver.database import TablesRelation
from pokerserver.models import Match, Player
from tests.utils import IntegrationTestCase, create_table, return_done_future


class TestSetPlayerActive(IntegrationTestCase):
    timeout = 0.001
    wait_timeout = 10 * timeout

    @classmethod
    async def create_match(cls):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 0),
            Player(table_id, 2, 'b', 10, [], 0),
            Player(table_id, 3, 'c', 10, [], 0),
            Player(table_id, 4, 'd', 10, [], 0)
        ]

        table = await create_table(table_id=table_id, players=players, small_blind=10, big_blind=20)

        match = Match(table)
        ServerConfig.set(timeout=cls.timeout)
        match.kick_if_current_player = Mock(side_effect=return_done_future())
        return match

    @gen_test
    async def test_sets_player_and_token(self):
        match = await self.create_match()
        uuid = uuid4()

        with patch('pokerserver.models.match.uuid4', return_value=uuid):
            await match.set_player_active(match.table.players[0])

        table = await TablesRelation.load_table_by_id(match.table.table_id)
        self.assertEqual(match.table.players[0].name, table['current_player'])
        self.assertEqual(str(uuid), table['current_player_token'])

        await asyncio.sleep(self.wait_timeout)  # wait for timeout task to finish

    @gen_test
    async def test_kicks_player_after_timeout(self):
        match = await self.create_match()

        await match.set_player_active(match.table.players[0])
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await asyncio.sleep(10 * ServerConfig.get('timeout'))

        match.kick_if_current_player.assert_called_once_with(
            match.table.players[0], token, 'timeout')

    @gen_test
    async def test_does_not_kick_if_disabled(self):
        match = await self.create_match()
        ServerConfig.set(timeout=None)
        await match.set_player_active(match.table.players[0])
        await asyncio.sleep(self.wait_timeout)
        match.kick_if_current_player.assert_not_called()
