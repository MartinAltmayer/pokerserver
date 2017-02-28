from http import HTTPStatus
import json
from unittest.mock import Mock

from tornado.testing import gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.models import Statistics
from tests.utils import IntegrationHttpTestCase


class TestStatisticsController(IntegrationHttpTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    async def create_statistics(self):
        await Statistics.increment_statistics("player 1", 1, 2, 3)
        await Statistics.increment_statistics("player 2", 10, 20, 30)
        await Statistics.increment_statistics("player 3", 100, 200, 300)

    @gen_test
    async def test_statistics_response(self):
        await self.create_statistics()
        response = await self.fetch_async('/statistics')
        self.assertEqual(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        response_data = json.loads(response_body)
        self.assertEqual(response_data, {
            'player 1': {
                'matches': 1,
                'buy_in': 2,
                'gain': 3
            },
            'player 2': {
                'matches': 10,
                'buy_in': 20,
                'gain': 30
            },
            'player 3': {
                'matches': 100,
                'buy_in': 200,
                'gain': 300
            }
        })
