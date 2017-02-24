from unittest.mock import Mock, call, patch

from nose.tools import assert_raises
from tornado.testing import AsyncTestCase, gen_test

from pokerserver.models import Match, Table
from tests.utils import return_done_future


class TestMatch(AsyncTestCase):
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
