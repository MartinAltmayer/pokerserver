from unittest.mock import Mock

from nose.tools import assert_equal

from pokerserver.models import Match, Table, Player


class TestMatch:
    def setUp(self):
        self.table = Mock(spec=Table)
        self.match = Match(self.table)

    def test_betting_round_finished_returns_false(self):
        configurations = [
            [self._mock_player(bet, False) for bet in range(8)],
            [self._mock_player(bet, False) for bet in [1, 2]],
            [self._mock_player(bet, False) for bet in [1, 1, 2]],
            [self._mock_player(bet, False) for bet in [1, 2, None]],
            [self._mock_player(bet, False) for bet in [None, None, None]]
        ]

        for configuration in configurations:
            yield self.check_betting_round_finished, configuration, False

    def test_betting_round_finished_returns_true(self):
        configurations = [
            [],
            [self._mock_player(0, False)],
            [self._mock_player(1, False)],
            [self._mock_player(10, False) for _ in range(2)],
            [self._mock_player(10, False) for _ in range(8)],
            [self._mock_player(bet, True) for bet in range(8)],
        ]

        for configuration in configurations:
            yield self.check_betting_round_finished, configuration, True

    @staticmethod
    def _mock_player(bet, has_folded):
        mock = Mock(spec=Player, bet=bet, has_folded=has_folded)
        mock.__repr__ = Mock(return_value='<bet {}, folded {}>'.format(bet, has_folded))
        return mock

    def check_betting_round_finished(self, configuration, expected_result):
        self.table.players = configuration
        assert_equal(expected_result, self.match.betting_round_finished())
