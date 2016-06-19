from tornado.testing import gen_test

from pokerserver.database import StatsRelation
from tests.integration.utils.integration_test import IntegrationTestCase


class TestStatsRelation(IntegrationTestCase):
    STATS = {
        'player1': (1, 2, 3),
        'player2': (4, 5, 6)
    }

    async def create_stats(self):
        for name, values in self.STATS.items():
            await self.db.execute("""
                INSERT INTO stats (player_name, matches, buy_in, gain)
                VALUES (?, ?, ?, ?)
                """, name, *values)

    @gen_test
    async def test_get_stats(self):
        await self.create_stats()
        stats = await StatsRelation.get_stats()
        self.assertDictEqual(self.STATS, stats)

    @gen_test
    async def test_increment_stats(self):
        await self.create_stats()
        await StatsRelation.increment_stats('player1', 1, 2, 3)
        stats = await StatsRelation.get_stats()
        expected_stats = self.STATS.copy()
        expected_stats['player1'] = (2, 4, 6)
        self.assertDictEqual(expected_stats, stats)
