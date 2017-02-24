from unittest import TestCase
from unittest.mock import patch

from pokerserver.client import CliClient, Table


class TestCliClient(TestCase):
    def setUp(self):
        self.client = CliClient('localhost', 1234, 5)

    @patch("builtins.print", autospec=True, side_effect=print)
    def test_print_table_info(self, mock_print):
        pots = [{'bets': {1: 12, 2: 13, 3: 14}}]
        self.client.table = Table('vegas', 'jack', [], round='preflop', pots=pots, open_cards=['14s', '3h', '2c'])

        self.client.print_table_info()
        mock_print.assert_called_with('PREFLOP Pots: 39 | Cards: 14s 3h 2c')
