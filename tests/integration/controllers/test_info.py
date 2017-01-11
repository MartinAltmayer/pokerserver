import json
from http import HTTPStatus

from nose.tools import assert_equals

from tests.integration.utils.integration_test import IntegrationHttpTestCase


class TestInfoController(IntegrationHttpTestCase):
    SETUP_DB_CONNECTION = False

    def test_info_response(self):
        # pylint: disable=no-member
        response = self.fetch('/info')
        assert_equals(response.code, HTTPStatus.OK.value)
        response_body = response.body.decode('utf-8')
        assert_equals(json.loads(response_body).keys(), {'name', 'description', 'version'})
