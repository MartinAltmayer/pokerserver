from unittest.mock import patch

from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from pokerserver.models import Match, Player, Round
from tests.utils import IntegrationTestCase, create_table, return_done_future


class TestKickCurrentPlayer(IntegrationTestCase):
    @staticmethod
    async def create_match():
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 0),
            Player(table_id, 2, 'b', 10, [], 0),
            Player(table_id, 3, 'c', 10, [], 0),
            Player(table_id, 4, 'd', 10, [], 0)
        ]

        table = await create_table(
            table_id=table_id, players=players, small_blind=1, big_blind=2, start_balance=20)

        return Match(table)

    # table continues with next round
    @gen_test
    async def test_kick_removes_player(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[3], token, 'reason')
        self.assertEqual(3, len(match.table.players))
        self.assertEqual({'a', 'b', 'c'}, {player.name for player in match.table.players})

    @gen_test
    async def test_kick_only_current_player(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[2], token, 'reason')
        self.assertEqual(4, len(match.table.players))

    @gen_test
    async def test_dont_kick_if_token_differs(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        await match.kick_if_current_player(match.table.players[2], 'thisisnotthetoken', 'reason')
        self.assertEqual(4, len(match.table.players))

    @patch('pokerserver.database.statistics.StatisticsRelation.increment_statistics', side_effect=return_done_future())
    @gen_test
    async def test_kick_increments_stats(self, increment_stats_mock):
        match = await self.create_match()
        await match.start(match.table.players[0])
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[3], token, 'reason')
        increment_stats_mock.assert_called_once_with('d', 1, 20, 10)

    @gen_test
    async def test_kick_sets_next_player(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[3], token, 'reason')
        self.assertEqual('a', match.table.current_player.name)

    @gen_test
    async def test_kick_dealer(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        await match.call('d')
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[0], token, 'reason')
        self.assertEqual('d', match.table.dealer.name)

    @gen_test
    async def test_kick_starts_next_round(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        await match.call('d')
        await match.call('a')
        await match.call('b')
        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(match.table.players[2], token, 'reason')

        self.assertEqual(Round.FLOP, match.table.round)
        self.assertEqual('b', match.table.current_player.name)

    @gen_test
    async def test_kick_closes_table_if_only_one_player_left(self):
        match = await self.create_match()
        await match.start(match.table.players[0])
        players_to_kick = [match.table.players[i] for i in [3, 0, 1]]
        for player in players_to_kick[:2]:
            token = await TablesRelation.get_current_player_token(match.table.table_id)
            await match.kick_if_current_player(player, token, 'reason')
        self.assertFalse(match.table.is_closed)

        token = await TablesRelation.get_current_player_token(match.table.table_id)
        await match.kick_if_current_player(players_to_kick[-1], token, 'reason')
        self.assertTrue(match.table.is_closed)
