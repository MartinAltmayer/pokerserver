from tornado.testing import gen_test

from pokerserver.database import TablesRelation
from tests.integration.utils.integration_test import IntegrationTestCase


class TestStatsRelation(IntegrationTestCase):
    TABLES = [
        {'name': 'table1', 'max_player_count': 9, 'players': ['frodo', 'pippin']},
        {'name': 'table2', 'max_player_count': 15, 'players': ['gandalf', 'bilbo']},
        {'name': 'empty table', 'max_player_count': 2, 'players': []}
    ]

    @gen_test
    async def test_create_table(self):
        await TablesRelation.create_table('Round Table', 30, ['Arthur', 'Percival'])
        row = await self.db.find_row('SELECT name, max_player_count, players FROM tables')
        self.assertEqual(('Round Table', 30, 'Arthur,Percival'), row)

    @gen_test
    async def test_load_all(self):
        for table in self.TABLES:
            await TablesRelation.create_table(**table)
        actual_tables = await TablesRelation.load_all()
        self.assertListEqual(self.TABLES, actual_tables)
