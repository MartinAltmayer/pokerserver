from unittest.mock import patch, call, Mock

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.database.tables import TableConfig
from pokerserver.models.table import Table
from tests.integration.utils.integration_test import return_done_future


class TestTable(AsyncTestCase):
    @patch('pokerserver.database.players.PlayersRelation.load_by_table_id')
    @patch('pokerserver.database.tables.TablesRelation.load_all')
    @patch('pokerserver.database.tables.TablesRelation.create_table', side_effect=return_done_future())
    @gen_test
    async def test_create_tables(self, create_table, load_all_tables, load_player_by_table_id):
        config = TableConfig(min_player_count=2, max_player_count=2, small_blind=13, big_blind=14)
        players = ['Percival', 'Tristan', 'Lancelot', 'Arthur']
        existing_table_names = ['Table1', 'Table3', 'SomeName']
        existing_players = [
            {
                'table_id': table_id,
                'position': position,
                'name': name,
                'balance': position * 1000,
                'cards': 'AcAd',
                'bet': position * 500,
                'last_seen': 0
            }
            for position, name in enumerate(players)
            for table_id in enumerate(existing_table_names)
        ]
        existing_tables = [
            {
                'table_id': table_id,
                'name': name,
                'config': TableConfig(4, 9, 12, 24),
                'remaining_deck': 'so many cards',
                'open_cards': 'turn',
                'main_pot': 3000,
                'side_pots': '',
                'current_player': 'Arthur',
                'dealer': 'Percival',
                'small_blind_player': 'Tristan',
                'big_blind_player': 'Lancelot',
                'highest_bet_player': None,
                'is_closed': False
            }
            for table_id, name in enumerate(existing_table_names)
        ]
        load_player_by_table_id.side_effect = return_done_future(existing_players)
        load_all_tables.side_effect = return_done_future(existing_tables)

        await Table.create_tables(2, config)
        create_table.assert_has_calls([
            call(
                table_id=3, name='Table2', config=config, remaining_deck=[], open_cards=[], main_pot=0,
                side_pots=[], current_player=None, dealer=None, small_blind_player=None,
                big_blind_player=None, highest_bet_player=None, is_closed=False
            ),
            call(
                table_id=4, name='Table4', config=config, remaining_deck=[], open_cards=[], main_pot=0,
                side_pots=[], current_player=None, dealer=None, small_blind_player=None,
                big_blind_player=None, highest_bet_player=None, is_closed=False
            )
        ])

    def test_player_left_of(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        for position, left_player_name in zip([1, 2, 5], ['p2', 'p5', 'p1']):
            player = table.get_player_at(position)
            self.assertEqual(left_player_name, table.player_left_of(player).name)

    def test_player_left_of_with_filter(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        player_filter = [table.get_player_at(1), table.get_player_at(5)]
        for position, left_player_name in zip([1, 2, 5], ['p5', 'p5', 'p1']):
            player = table.get_player_at(position)
            self.assertEqual(left_player_name, table.player_left_of(player, player_filter).name)

    def test_player_left_of_fails(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        player = table.get_player_at(1)
        with self.assertRaises(ValueError):
            table.player_left_of(player, [])
        with self.assertRaises(ValueError):
            table.player_left_of(player, [player])
