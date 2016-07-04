from http import HTTPStatus
from tornado.web import HTTPError, MissingArgumentError

from pokerserver.controllers.base import BaseController, authenticated
from pokerserver.models import Table

TABLE_NAME_PATTERN = "([^/]+)"


class TableController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN

    async def get(self, name):  # pylint: disable=arguments-differ
        table = await Table.load_by_name(name)
        self.write(table.to_dict(self.player_name))


class JoinController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/join'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        position = self._get_position()
        match = await self.load_match(table_name)
        try:
            await match.join(self.player_name, position, self.settings['args'].start_balance)
        except ValueError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))

    def _get_position(self):
        try:
            return int(self.get_query_argument('position'))
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "position"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid position')
