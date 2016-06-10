import json
from http import HTTPStatus
from unittest.mock import Mock

from nose.tools import assert_equals
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application

from pokerserver.controllers import HANDLERS


class TestInfoController(AsyncHTTPTestCase):
    def get_app(self):
        return Application(HANDLERS, args=Mock())

    def test_info_response(self):
        response = self.fetch('/info')
        assert_equals(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        assert_equals(set(json.loads(response_body).keys()), {'name', 'description', 'version'})
