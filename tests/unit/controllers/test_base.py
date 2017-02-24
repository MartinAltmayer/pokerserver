from unittest.mock import Mock, patch

from tornado.testing import AsyncTestCase, gen_test

from pokerserver.controllers import BaseController
from tests.utils import return_done_future


class TestBaseController(AsyncTestCase):
    def setUp(self):
        super().setUp()
        mock_application = Mock()
        mock_application.ui_methods = {}
        mock_application.settings = {'args': Mock(turn_delay=1000)}
        self.controller = BaseController(mock_application, Mock())

    @patch('pokerserver.models.table.Table.load_by_name')
    @gen_test
    async def test_load_match(self, load_by_name_mock):
        load_by_name_mock.side_effect = return_done_future(Mock())
        match = await self.controller.load_match('table name')
        self.assertEqual(1000, match.turn_delay)
        load_by_name_mock.assert_called_once_with('table name')
