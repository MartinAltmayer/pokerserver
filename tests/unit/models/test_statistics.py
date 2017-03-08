from unittest.mock import patch

from tornado.testing import AsyncTestCase, gen_test

from pokerserver.models import PlayerStatistics, Statistics
from tests.utils import return_done_future


class TestStatistics(AsyncTestCase):
    def setUp(self):
        super().setUp()
        self.player_statistics = [
            PlayerStatistics('player {}'.format(index + 1), index + 1, index + 11, index + 21) for index in range(3)
        ]
        self.statistics = Statistics(self.player_statistics)

    def test_to_dict(self):
        result = self.statistics.to_dict()
        self.assertEqual(result, {
            'player 1': {
                'matches': 1,
                'buy_in': 11,
                'gain': 21
            },
            'player 2': {
                'matches': 2,
                'buy_in': 12,
                'gain': 22
            },
            'player 3': {
                'matches': 3,
                'buy_in': 13,
                'gain': 23
            }
        })

    @patch('pokerserver.database.statistics.StatisticsRelation.load_all', side_effect=return_done_future([]))
    @gen_test
    async def test_load(self, load_all_mock):
        await Statistics.load()
        load_all_mock.assert_called_once_with()

    @patch('pokerserver.database.statistics.StatisticsRelation.init_statistics', side_effect=return_done_future([]))
    @gen_test
    async def test_init_statistics(self, init_statistics_mock):
        await Statistics.init_statistics('player xyz')
        init_statistics_mock.assert_called_once_with('player xyz')

    @patch('pokerserver.database.statistics.StatisticsRelation.increment_statistics',
           side_effect=return_done_future([]))
    @gen_test
    async def test_increment_statistics(self, increment_statistics_mock):
        await Statistics.increment_statistics('player xyz', 1, 2, 3)
        increment_statistics_mock.assert_called_once_with('player xyz', 1, 2, 3)
