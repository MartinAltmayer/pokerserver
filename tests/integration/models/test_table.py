from unittest.mock import patch, call

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.models.table import Table
from tests.integration.utils.integration_test import return_done_future


class TestTable(AsyncTestCase):
    @patch('pokerserver.database.players.PlayersRelation.load_by_table_id')
    @patch('pokerserver.database.tables.TablesRelation.load_all')
    @patch('pokerserver.database.tables.TablesRelation.create_table', side_effect=return_done_future())
    @gen_test
    async def test_create_tables(self, create_table, load_all_tables, load_player_by_table_id):
        max_player_count = 2
        small_blind = 13
        big_blind = 14
        players = ['Percival', 'Tristan', 'Lancelot', 'Arthur']
        existing_table_names = ['Table 1', 'Table 3', 'SomeName']
        existing_players = [
            {
                'table_id': table_id,
                'position': position,
                'name': name,
                'balance': position * 1000,
                'cards': 'AcAd',
                'bet': position * 500
            }
            for position, name in enumerate(players)
            for table_id in enumerate(existing_table_names)
        ]
        existing_tables = [
            {
                'table_id': table_id,
                'name': name,
                'max_player_count': 10,
                'remaining_deck': 'so many cards',
                'small_blind': 12,
                'big_blind': 24,
                'open_cards': 'turn',
                'main_pot': 3000,
                'side_pots': '',
                'current_player': 'Arthur',
                'dealer': 'Percival',
                'small_blind_player': 'Tristan',
                'big_blind_player': 'Lancelot',
                'is_closed': False
            }
            for table_id, name in enumerate(existing_table_names)
        ]
        load_player_by_table_id.side_effect = return_done_future(existing_players)
        load_all_tables.side_effect = return_done_future(existing_tables)

        await Table.create_tables(2, max_player_count, small_blind, big_blind)
        create_table.assert_has_calls([
            call(3, 'Table 2', max_player_count, '', small_blind, big_blind, '', 0, '', None, None, None, None, False),
            call(4, 'Table 4', max_player_count, '', small_blind, big_blind, '', 0, '', None, None, None, None, False)
        ])
