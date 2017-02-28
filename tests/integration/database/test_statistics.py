from tornado.testing import gen_test

from pokerserver.database import StatisticsRelation
from tests.utils import IntegrationTestCase


class TestStatisticsRelation(IntegrationTestCase):
    STATISTICS = [
        {
            'player_name': 'player1',
            'matches': 1,
            'buy_in': 2,
            'gain': 3
        },
        {
            'player_name': 'player2',
            'matches': 4,
            'buy_in': 5,
            'gain': 6
        }
    ]

    async def create_statistics(self):
        for player_stats in self.STATISTICS:
            await StatisticsRelation.init_statistics(**player_stats)

    @gen_test
    async def test_init_and_get_statistics(self):
        await self.create_statistics()
        stats = await StatisticsRelation.load_all()
        self.assertEqual(self.STATISTICS, stats)

    @gen_test
    async def test_increment_statistics(self):
        await self.create_statistics()
        await StatisticsRelation.increment_statistics('player1', 1, 2, 3)
        stats = await StatisticsRelation.load_all()
        expected_stats = self.STATISTICS.copy()
        expected_stats[0] = {
            'player_name': 'player1',
            'matches': 2,
            'buy_in': 4,
            'gain': 6
        }
        self.assertEqual(expected_stats, sorted(stats, key=lambda player_stats: player_stats['player_name']))

    @gen_test
    async def test_increment_statistics_initializes(self):
        await StatisticsRelation.increment_statistics('player1', 1, 2, 3)
        stats = await StatisticsRelation.load_all()
        expected_stats = [
            {
                'player_name': 'player1',
                'matches': 1,
                'buy_in': 2,
                'gain': 3
            }
        ]
        self.assertEqual(expected_stats, sorted(stats, key=lambda player_stats: player_stats['player_name']))
