from unittest.mock import patch, call

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.models.table import Table
from tests.integration.utils.integration_test import return_done_future


class TestTable(AsyncTestCase):
    @patch('pokerserver.database.tables.TablesRelation.load_all')
    @patch('pokerserver.database.tables.TablesRelation.create_table', side_effect=return_done_future())
    @gen_test
    async def test_create_tables(self, create_table, load_all):
        max_player_count = 2
        existing_table_names = ['Table 1', 'Table 3', 'SomeName']
        existing_tables = [{'name': name, 'max_player_count': max_player_count, 'players': ''}
                           for name in existing_table_names]
        load_all.side_effect = return_done_future(existing_tables)


        await Table.create_tables(2, max_player_count)
        create_table.assert_has_calls([
            call('Table 2', max_player_count, []),
            call('Table 4', max_player_count, [])
        ])
