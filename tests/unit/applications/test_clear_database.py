# pylint: disable=no-self-use

import sys
from asyncio import new_event_loop, set_event_loop
from unittest import TestCase
from unittest.mock import patch, Mock

from pokerserver.applications.clear_database import main
from tests.utils import return_done_future


class TestClearDatabase(TestCase):
    def setUp(self):
        set_event_loop(new_event_loop())

    @patch.object(sys, 'argv', ['clear_database', 'path_to_db'])
    @patch('pokerserver.applications.clear_database.clear_relations')
    @patch('pokerserver.applications.clear_database.Database.connect')
    def test_main(self, connect_mock, clear_relations_mock):
        close_connection_mock = Mock(side_effect=return_done_future())
        connect_mock.side_effect = return_done_future(Mock(close_connection=close_connection_mock))
        clear_relations_mock.side_effect = return_done_future()
        main()
        connect_mock.assert_called_once_with('path_to_db')
        clear_relations_mock.assert_called_once_with(exclude=[])
        close_connection_mock.assert_called_once_with()
