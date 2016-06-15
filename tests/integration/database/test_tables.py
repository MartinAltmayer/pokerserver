from tornado.testing import gen_test

from pokerserver.database.tables import TablesTable
from tests.integration.utils.integration_test import IntegrationTestCase


class TestStatsTable(IntegrationTestCase):
    TABLES = [
        {'name': 'table1', 'max_player_count': 9, 'players': ['frodo', 'pippin']},
        {'name': 'table2', 'max_player_count': 15, 'players': ['gandalf', 'bilbo']}
    ]

    @gen_test
    async def test_create_table(self):
        await TablesTable.create_table('Round Table', 30, ['Arthur', 'Percival'])
        row = await self.db.find_row('SELECT name, max_player_count, players FROM tables')
        self.assertEqual(('Round Table', 30, 'Arthur,Percival'), row)

    @gen_test
    async def test_get_tables(self):
        for table in self.TABLES:
            await TablesTable.create_table(**table)
        actual_tables = await TablesTable.get_tables()
        self.assertListEqual(self.TABLES, actual_tables)
