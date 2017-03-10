from http import HTTPStatus

from pokerserver.models import InvalidTurnError, PositionOccupiedError, Table, TableNotFoundError
from .base import BaseController, HTTPError, authenticated

TABLE_NAME_PATTERN = r'([^/]+)'


class TableController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/?'

    async def get(self, name):  # pylint: disable=arguments-differ
        try:
            table = await Table.load_by_name(name)
            self.write(table.to_dict(self.player_name))
        except TableNotFoundError:
            raise HTTPError(HTTPStatus.NOT_FOUND, 'Table not found')


class JoinController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/actions/join/?'

    @authenticated
    async def post(self, table_name):  # pylint: disable=arguments-differ
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
            return int(self.get_body()['position'])
        except KeyError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "position"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid position')


class FoldController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/actions/fold/?'

    @authenticated
    async def post(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.fold(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class CallController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/actions/call/?'

    @authenticated
    async def post(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.call(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class CheckController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/actions/check/?'

    @authenticated
    async def post(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        try:
            await match.check(self.player_name)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))


class RaiseController(BaseController):
    route = r'/table/' + TABLE_NAME_PATTERN + r'/actions/raise/?'

    @authenticated
    async def post(self, table_name):  # pylint: disable=arguments-differ
        match = await self.load_match(table_name)
        amount = self._get_amount()
        try:
            await match.raise_bet(self.player_name, amount)
        except InvalidTurnError as error:
            raise HTTPError(HTTPStatus.BAD_REQUEST, str(error))

    def _get_amount(self):
        try:
            return int(self.get_body()['amount'])
        except KeyError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "amount"')
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid amount')
