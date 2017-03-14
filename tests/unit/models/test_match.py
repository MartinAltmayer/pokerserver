from unittest import TestCase
from unittest.mock import Mock, call, patch

from nose.tools import assert_raises
from tornado.testing import AsyncTestCase, gen_test

from pokerserver.database import PlayerState, TableConfig, TableState
from pokerserver.models import Match, Player, Table
from tests.utils import return_done_future


@patch('pokerserver.models.player.Player.sit_down', side_effect=return_done_future())
@patch('pokerserver.models.player.Player.load_by_name', side_effect=return_done_future(Mock()))
@patch('pokerserver.database.tables.TablesRelation.add_joined_player', side_effect=return_done_future())
@patch('pokerserver.models.match.Match.start', side_effect=return_done_future())
class TestJoin(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.players = [Mock(position=1)]
        self.config = Mock(min_player_count=2, max_player_count=4, big_blind=2, small_blind=1, start_balance=10)
        self.table = Table(1, 'table', self.config, players=self.players)
        self.match = Match(self.table)

    @gen_test
    async def test_join_starts_game_if_not_running(self, start_mock, *_):
        await self.match.join('horst', 2)
        start_mock.assert_called_once_with()

    @gen_test
    async def test_join_does_not_restart_running_games(self, start_mock, *_):
        self.table.state = TableState.RUNNING_GAME
        await self.match.join('horst', 2)
        start_mock.assert_not_called()


class TestPayments(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.players = [
            Mock(
                position=position,
                balance=balance,
                increase_bet=Mock(side_effect=return_done_future()),
                all_in=Mock(side_effect=return_done_future())
            )
            for position, balance in [(1, 10), (2, 10), (5, 10)]
        ]
        self.config = Mock(min_player_count=2, max_player_count=4, big_blind=2, small_blind=1, start_balance=10)
        self.table = Table(1, 'table', self.config, players=self.players)
        self.table.increase_pot = Mock(side_effect=return_done_future())
        self.match = Match(self.table)

    @patch('pokerserver.models.match.Match.make_player_pay', side_effect=return_done_future())
    @gen_test
    async def test_pay_blinds(self, mock_make_player_pay):
        await self.match.pay_blinds(self.players[2], self.players[0])
        mock_make_player_pay.assert_has_calls([
            call(self.players[2], 1),
            call(self.players[0], 2)
        ])

    @gen_test
    async def test_make_player_pay(self):
        await self.match.make_player_pay(self.players[2], 5)
        self.players[2].increase_bet.assert_called_once_with(5)
        self.players[2].all_in.assert_not_called()
        self.table.increase_pot.assert_called_once_with(5, 5)

    @gen_test
    async def test_make_player_pay_negative_amount(self):
        with assert_raises(AssertionError):
            await self.match.make_player_pay(self.players[2], -5)


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
        self.assertIs(players[2], self.match.find_start_player())

        self.assertIsNone(self.match.find_next_player(players[1]))

    def test_find_next_player_has_already_played_but_not_highest_bet(self):
        players = self.sorted_players
        self.assertIs(players[5], self.table.dealer)
        self.assertIs(players[2], self.match.find_start_player())
        players[3].bet = 10

        self.assertIs(players[2], self.match.find_next_player(players[1]))

    def test_find_next_player_heads_up(self):
        self.table.players = players = self.create_players(2)
        self.table.dealer = players[0]

        self.assertEqual(players[1], self.match.find_next_player(players[0]))
        self.assertIsNone(self.match.find_next_player(players[1]))

        self.assertEqual(players[1], self.match.find_next_player(players[0]))
