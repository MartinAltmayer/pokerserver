from http import HTTPStatus

from tornado.web import MissingArgumentError

from pokerserver.models import Table, PositionOccupiedError, InvalidTurnError
from .base import BaseController, authenticated, HTTPError

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
            await match.join(self.player_name, position)
        except PositionOccupiedError:
            raise HTTPError(HTTPStatus.CONFLICT, 'Position occupied')
        except ValueError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))

    def _get_position(self):
        try:
            return int(self.get_query_argument('position'))
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "position"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid position')


class FoldController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/fold'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.fold(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class CallController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/call'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.call(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class CheckController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/check'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.check(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class RaiseController(BaseController):
    route = '/table/' + TABLE_NAME_PATTERN + '/raise'

    @authenticated
    async def get(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        amount = self._get_amount()
        try:
            await match.raise_bet(self.player_name, amount)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))

    def _get_amount(self):
        try:
            return int(self.get_query_argument('amount'))
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "amount"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid amount')
