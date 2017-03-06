import asyncio
from unittest import TestCase
from unittest.mock import Mock, patch
from uuid import uuid4

from tornado.testing import gen_test

from pokerserver.configuration import ServerConfig
from pokerserver.database import PlayerState, TableConfig, TablesRelation
from pokerserver.models import Match, Player, Table
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


class TestFindNextPlayer(TestCase):
    def setUp(self):
        super().setUp()
        config = TableConfig(
            min_player_count=2, max_player_count=4, big_blind=2, small_blind=1, start_balance=10)
        self.table = Table(1, 'test', config)
        self.table.players = self.create_players(6)
        self.sorted_players = sorted(self.table.players, key=lambda p: p.position)
        self.table.dealer = self.table.players[0]
        self.match = Match(self.table)

    @staticmethod
    def create_players(count):
        # make sure that the positional order differs from the order in the list
        players = [
            Mock(spec=Player, position=count - position, bet=0, state=PlayerState.PLAYING)
            for position in range(count)
        ]
        for player in players:
            player.name = 'p{}'.format(player.position)
        return players

    def test_find_next_player_basic(self):
        players = self.sorted_players
        self.assertEqual(players[3], self.match.find_next_player(players[2]))
        self.assertEqual(players[0], self.match.find_next_player(players[5]))

    def test_find_next_player_folded(self):
        players = self.sorted_players
        players[3].state = PlayerState.FOLDED
        self.assertEqual(players[4], self.match.find_next_player(players[2]))

    def test_find_next_player_sitting_out(self):
        players = self.sorted_players
        players[3].state = PlayerState.SITTING_OUT
        self.assertEqual(players[4], self.match.find_next_player(players[2]))

    def test_find_next_player_all_folded(self):
        players = self.sorted_players
        for player in players:
            player.state = PlayerState.FOLDED
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_all_sitting_out(self):
        players = self.sorted_players
        for player in players:
            player.state = PlayerState.SITTING_OUT
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_all_folded_except_current(self):
        players = self.sorted_players
        for player in players[1:]:
            player.state = PlayerState.FOLDED
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_has_already_played_and_highest_bet(self):
        players = self.sorted_players
        self.assertIs(players[5], self.table.dealer)
        self.assertIs(players[2], self.match.find_start_player(self.table.dealer, self.table.round))

        self.assertIsNone(self.match.find_next_player(players[1]))

    def test_find_next_player_has_already_played_but_not_highest_bet(self):
        players = self.sorted_players
        self.assertIs(players[5], self.table.dealer)
        self.assertIs(players[2], self.match.find_start_player(self.table.dealer, self.table.round))
        players[3].bet = 10

        self.assertIs(players[2], self.match.find_next_player(players[1]))

    def test_find_next_player_heads_up(self):
        self.table.players = players = self.create_players(2)
        self.table.dealer = players[0]

        self.assertEqual(players[1], self.match.find_next_player(players[0]))
        self.assertIsNone(self.match.find_next_player(players[1]))

        self.assertEqual(players[1], self.match.find_next_player(players[0]))
