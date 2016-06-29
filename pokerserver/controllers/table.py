from http import HTTPStatus
from tornado.web import HTTPError, MissingArgumentError

from pokerserver.controllers.base import BaseController, authenticated
from pokerserver.models import Table, TableNotFoundError

TABLE_NAME_PATTERN = "([^/]+)"


class TableController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN

    async def get(self, name):  # pylint: disable=arguments-differ
        player = None
        table = await Table.load_by_name(name)
        self.write(table.to_dict(player))


class JoinController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/join'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        position = self._get_position()
        table = await self._get_table(table_name)
        try:
            await table.join(self.player_name, position, self.settings['args'].start_balance)
        except ValueError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))

    def _get_position(self):
        try:
            return int(self.get_query_argument('position'))
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "position"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid position')

    async def _get_table(self, table_name):
        try:
            return await Table.load_by_name(table_name)
        except TableNotFoundError:
            raise HTTPError(HTTPStatus.NOT_FOUND, 'Table not found')
