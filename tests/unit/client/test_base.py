from unittest import TestCase
from unittest.mock import patch, Mock

from nose.tools import assert_equal, assert_false, assert_true, assert_raises

from pokerserver.client import BaseClient, TableInfo


class TestTableInfo(TestCase):
    def setUp(self):
        players = {str(i): 'player {}'.format(i) for i in range(1, 5)}
        self.table_info = TableInfo('table 1', 2, 6, players)

    def test_is_free_for(self):
        assert_true(self.table_info.is_free_for('yoda'))
        assert_false(self.table_info.is_free_for('player 1'))

    def test_find_free_positions(self):
        assert_equal(self.table_info.find_free_positions(), [5, 6])

    def test_find_free_position(self):
        assert_equal(self.table_info.find_free_position(), 5)

    def test_find_free_position_table_full(self):
        self.table_info.max_player_count = 4
        with assert_raises(ValueError):
            self.table_info.find_free_position()


@patch('pokerserver.client.base.urlopen')
class TestBaseClient(TestCase):
    def setUp(self):
        self.response = Mock(code=200, read=Mock(return_value='{ "response": "ok" }'.encode()))
        self.base_client = BaseClient('localhost', 55555)

    def test_fetch(self, urlopen_mock):
        urlopen_mock.return_value = self.response
        assert_equal('{ "response": "ok" }', self.base_client.fetch("/test_url", as_json=False))

    def test_fetch_as_json(self, urlopen_mock):
        urlopen_mock.return_value = self.response
        assert_equal({'response': 'ok'}, self.base_client.fetch("/test_url", as_json=True))
        urlopen_mock.assert_called_once_with('http://localhost:55555/test_url')

    def test_fetch_table(self, urlopen_mock):
        response = '''
        {
            "players": [],
            "small_blind": 1,
            "big_blind": 2,
            "round": "preflop",
            "open_cards": [],
            "pots": [
                {
                    "bets": {}
                }
            ],
            "current_player": null,
            "dealer": null,
            "is_closed": false,
            "can_join": true
        }
        '''
        urlopen_mock.return_value = Mock(code=200, read=Mock(return_value=response.encode()))
        table = self.base_client.fetch_table('table 1')
        assert_equal("table 1", table.name)
        assert_equal('preflop', table.round)
        urlopen_mock.assert_called_once_with('http://localhost:55555/table/table 1')

    def test_fetch_tables(self, urlopen_mock):
        response = '''
        {
            "tables": [
                {
                    "name": "table 1",
                    "min_player_count": 3,
                    "max_player_count": 42,
                    "players": {}
                }
            ]
        }
        '''
        urlopen_mock.return_value = Mock(code=200, read=Mock(return_value=response.encode()))
        tables_infos = self.base_client.fetch_tables()
        assert_equal(1, len(tables_infos))
        urlopen_mock.assert_called_once_with('http://localhost:55555/tables')

    def test_find_free_table(self, _):  # pylint: disable=no-self-use
        tables = [
            TableInfo('table 1', 1, 3, {1: 'lynn', 2: 'brian'})
        ]
        BaseClient.find_free_table(tables, ['alf', 'willy', 'kate'])

    def test_join_table(self, urlopen_mock):
        urlopen_mock.return_value = self.response
        self.base_client.join_table(TableInfo("table 1", 1, 3, {}), "player 1", 42, "uuid")
        urlopen_mock.assert_called_once_with(
            'http://localhost:55555/table/table 1/join?player_name=player 1&position=42&uuid=uuid'
        )
