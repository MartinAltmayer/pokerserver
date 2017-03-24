import json
from http import HTTPStatus
from unittest.mock import Mock
from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.models import Player
from tests.utils import IntegrationHttpTestCase, create_table


class TestDevCookieController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock(password='secret'))

    def test_devcookie_fail(self):
        response = self.fetch('/devcookie?password=wrong')
        self.assertEqual(response.code, HTTPStatus.BAD_REQUEST.value)
        self.assertNotIn('Set-Cookie', response.headers)

    def test_devcookie_success(self):
        response = self.fetch('/devcookie?password=secret')
        self.assertEqual(response.code, HTTPStatus.NO_CONTENT.value)
        self.assertEqual(
            'devcookie=secret; HttpOnly; Path=/',
            response.headers['Set-Cookie']
        )


class TestFrontendDataController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock(password='secret'))

    async def async_setup(self):
        self.table_id = 1
        self.players = [
            Player(self.table_id, 1, 'a', 10, ['Ah', 'Ac'], 2),
            Player(self.table_id, 2, 'b', 20, ['Kh', 'Kc'], 3),
            Player(self.table_id, 5, 'c', 20, ['Qh', 'Qc'], 4)
        ]
        await create_table(table_id=self.table_id, name='Table1', players=self.players)

    @gen_test
    async def test_get_unauthorized(self):
        await self.async_setup()
        response = await self.fetch_async('/fedata/Table1', raise_error=False)
        self.assertEqual(response.code, HTTPStatus.UNAUTHORIZED.value)

    @gen_test
    async def test_get_no_table(self):
        await self.async_setup()
        response = await self.fetch_async(
            '/fedata/Table1234',
            headers={'Cookie': 'devcookie=secret'},
            raise_error=False
        )
        self.assertEqual(response.code, HTTPStatus.NOT_FOUND.value)

    @gen_test
    async def test_get_authorized(self):
        await self.async_setup()
        response = await self.fetch_async('/fedata/Table1', headers={'Cookie': 'devcookie=secret'})
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        data = json.loads(response_body)

        expected_data = {
            'players': [
                {
                    'balance': player.balance,
                    'bet': player.bet,
                    'cards': player.cards,
                    'current': False,
                    'dealer': False,
                    'state': 'playing',
                    'name': player.name,
                    'position': player.position
                } for player in self.players
            ],
            'openCards': [],
            'pot': 0
        }
        self.assertEqual(expected_data, data)


class TestIndexController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock(password='secret'))

    async def async_setup(self):
        await create_table(name='Table1')

    @gen_test
    async def test_get_unauthorized(self):
        await self.async_setup()
        response = await self.fetch_async('/gui/Table1', raise_error=False)
        self.assertEqual(response.code, HTTPStatus.UNAUTHORIZED.value)

    @gen_test
    async def test_get_no_table(self):
        await self.async_setup()
        response = await self.fetch_async(
            '/gui/Table1234',
            headers={'Cookie': 'devcookie=secret'},
            raise_error=False
        )
        self.assertEqual(response.code, HTTPStatus.NOT_FOUND.value)

    @gen_test
    async def test_get_authorized(self):
        await self.async_setup()
        response = await self.fetch_async('/gui/Table1', headers={'Cookie': 'devcookie=secret'})
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        self.assertIn('<html', response_body)
