from unittest.mock import patch, call, Mock

from tornado.testing import gen_test, AsyncTestCase

from pokerserver.database.tables import TableConfig
from pokerserver.models.table import Table, Player
from tests.utils import return_done_future, create_table, IntegrationTestCase


class TestTable(AsyncTestCase):
    @patch('pokerserver.database.players.PlayersRelation.load_by_table_id')
    @patch('pokerserver.database.tables.TablesRelation.load_all')
    @patch('pokerserver.database.tables.TablesRelation.create_table', side_effect=return_done_future())
    @gen_test
    async def test_create_tables(self, create_table, load_all_tables, load_player_by_table_id):
        config = TableConfig(
            min_player_count=2, max_player_count=2, small_blind=13, big_blind=14, start_balance=10)
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
                'config': TableConfig(4, 9, 12, 24, 10),
                'remaining_deck': 'so many cards',
                'open_cards': 'turn',
                'main_pot': 3000,
                'side_pots': '',
                'current_player': 'Arthur',
                'dealer': 'Percival',
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
                side_pots=[], current_player=None, current_player_token=None, dealer=None,
                is_closed=False, joined_players=None
            ),
            call(
                table_id=4, name='Table4', config=config, remaining_deck=[], open_cards=[], main_pot=0,
                side_pots=[], current_player=None, current_player_token=None, dealer=None,
                is_closed=False, joined_players=None
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

    def test_player_right_of(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        for position, left_player_name in zip([1, 2, 5], ['p5', 'p1', 'p2']):
            player = table.get_player_at(position)
            self.assertEqual(left_player_name, table.player_right_of(player).name)

    def test_player_right_of_with_filter(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        player_filter = [table.get_player_at(1), table.get_player_at(5)]
        for position, left_player_name in zip([1, 2, 5], ['p5', 'p1', 'p1']):
            player = table.get_player_at(position)
            self.assertEqual(left_player_name, table.player_right_of(player, player_filter).name)

    def test_player_right_of_fails(self):
        players = [Mock(position=position) for position in (1, 2, 5)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        table = Table(table_id=1, name='a table', config=Mock(), players=players)

        player = table.get_player_at(1)
        with self.assertRaises(ValueError):
            table.player_right_of(player, [])
        with self.assertRaises(ValueError):
            table.player_right_of(player, [player])

    def test_player_positions_between(self):
        all_players = [Mock(position=p) for p in [7, 3, 5, 2, 6]]
        table = Table(table_id=1, name='a table', config=Mock(), players=all_players)

        self.assertEqual([2], table.player_positions_between(2, 2))
        self.assertEqual([3, 5, 6], table.player_positions_between(3, 6))
        self.assertEqual([6, 7, 2, 3], table.player_positions_between(6, 3))


class TestCloseTable(IntegrationTestCase):
    @patch('pokerserver.database.players.PlayersRelation.delete_player', side_effect=return_done_future())
    @gen_test
    async def test_close_table(self, delete_player_mock):
        table_id = 17
        players = [
            Player(table_id, 1, 'a', 0, [], 0),
            Player(table_id, 2, 'b', 0, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players)

        await table.close()

        table = await Table.load_by_name(table.name)
        self.assertTrue(table.is_closed)
        delete_player_mock.assert_has_calls(
            [call(table_id, player.position) for player in players], any_order=True)
