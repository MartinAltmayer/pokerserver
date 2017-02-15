from http import HTTPStatus
from unittest.mock import patch

from tornado.testing import gen_test

from pokerserver.database import DuplicateKeyError
from tests.utils import IntegrationHttpTestCase, return_done_future


class TestUUIDController(IntegrationHttpTestCase):
    @patch('pokerserver.database.UUIDsRelation.add_uuid', side_effect=return_done_future())
    @patch('uuid.uuid4', return_value='123-456')
    @gen_test
    async def test_uuid(self, _, add_uuid_mock):
        response = await self.fetch_async('/uuid?player_name=hans')
        self.assertEqual(response.code, HTTPStatus.OK.value)
        self.assertEqual(response.body.decode(), '123-456')
        add_uuid_mock.assert_called_once_with('123-456', 'hans')

    @gen_test
    async def test_uuid_invalid_name(self):
        response = await self.fetch_async('/uuid?player_name=aa', raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)

    @patch('pokerserver.database.UUIDsRelation.add_uuid',
           side_effect=return_done_future(exception=DuplicateKeyError()))
    @patch('uuid.uuid4', return_value='123-456')
    @gen_test
    async def test_uuid_fail_on_duplicate(self, *_):
        response = await self.fetch_async('/uuid?player_name=hans', raise_error=False)
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)
