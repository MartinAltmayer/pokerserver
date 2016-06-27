from http import HTTPStatus
from tornado.web import RequestHandler, HTTPError, MissingArgumentError

from pokerserver.controllers.base import BaseController, authenticated
from pokerserver.models import Table, TableNotFoundError

TABLE_NAME_PATTERN = "[^/]+"


class TableController(BaseController):
    route = r'/table/([^/]+)'

    async def get(self, name):  # pylint: disable=arguments-differ
        player = None
        table = await Table.load_by_name(name)
        self.write(table.to_dict(player))
