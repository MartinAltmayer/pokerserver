from unittest import TestCase
from unittest.mock import Mock, patch

from nose.tools import assert_equal, assert_false, assert_raises, assert_true

from pokerserver.client import BaseClient, TableInfo


class TestTableInfo(TestCase):
    def setUp(self):
        players = {str(i): 'player {}'.format(i) for i in range(1, 5)}
        self.table_info = TableInfo('table 1', 2, 6, players, 'waiting for players')

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


class TestBaseClient(TestCase):
    def setUp(self):
        self.response = Mock(status_code=200, json=Mock(return_value={'response': 'ok'}), text='{ "response": "ok" }')
        self.base_client = BaseClient('localhost', 55555)

    @patch('pokerserver.client.base.get')
    def test_fetch(self, get_mock):
        get_mock.return_value = self.response
        assert_equal('{ "response": "ok" }', self.base_client.fetch("/test_url", as_json=False))

    @patch('pokerserver.client.base.get')
    def test_fetch_as_json(self, urlopen_mock):
        urlopen_mock.return_value = self.response
        assert_equal({'response': 'ok'}, self.base_client.fetch("/test_url", as_json=True))
        urlopen_mock.assert_called_once_with('http://localhost:55555/test_url')

    @patch('pokerserver.client.base.get')
    def test_fetch_table(self, get_mock):
        self.response.json.return_value = {
            'players': [],
            'small_blind': 1,
            'big_blind': 2,
            'round': 'preflop',
            'open_cards': [],
            'pots': [
                {
                    'bets': {}
                }
            ],
            'current_player': None,
            'dealer': None,
            'is_closed': False,
            'can_join': True
        }
        get_mock.return_value = self.response
        table = self.base_client.fetch_table('table 1')
        assert_equal("table 1", table.name)
        assert_equal('preflop', table.round)
        get_mock.assert_called_once_with('http://localhost:55555/table/table 1')

    @patch('pokerserver.client.base.get')
    def test_fetch_tables(self, get_mock):
        self.response.json.return_value = {
            'tables': [
                {
                    'name': 'table 1',
                    'min_player_count': 3,
                    'max_player_count': 42,
                    'players': {},
                    'state': 'running game'
                }
            ]
        }
        get_mock.return_value = self.response
        tables_infos = self.base_client.fetch_tables()
        assert_equal(1, len(tables_infos))
        get_mock.assert_called_once_with('http://localhost:55555/tables')

    def test_find_free_table(self):  # pylint: disable=no-self-use
        tables = [
            TableInfo('table 1', 1, 3, {1: 'lynn', 2: 'brian'}, 'waiting for players')
        ]
        BaseClient.find_free_table(tables, ['alf', 'willy', 'kate'])

    @patch('pokerserver.client.base.post')
    def test_join_table(self, post_mock):
        self.base_client.join_table(TableInfo("table 1", 1, 3, {}, 'waiting for players'), 42, "uuid")
        post_mock.assert_called_once_with(
            'http://localhost:55555/table/table 1/actions/join?uuid=uuid',
            json={'position': 42}
        )

    @patch('pokerserver.client.base.post')
    def test_fold(self, post_mock):
        self.base_client.fold("table 1", "uuid")
        post_mock.assert_called_once_with('http://localhost:55555/table/table 1/actions/fold?uuid=uuid')

    @patch('pokerserver.client.base.post')
    def test_check(self, post_mock):
        self.base_client.check("table 1", "uuid")
        post_mock.assert_called_once_with('http://localhost:55555/table/table 1/actions/check?uuid=uuid')

    @patch('pokerserver.client.base.post')
    def test_call(self, post_mock):
        self.base_client.call("table 1", "uuid")
        post_mock.assert_called_once_with('http://localhost:55555/table/table 1/actions/call?uuid=uuid')

    @patch('pokerserver.client.base.post')
    def test_raise_bet(self, post_mock):
        self.base_client.raise_bet("table 1", "uuid", 42)
        post_mock.assert_called_once_with(
            'http://localhost:55555/table/table 1/actions/raise?uuid=uuid',
            json={'amount': 42}
        )
