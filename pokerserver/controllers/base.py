import asyncio
import functools
from http import HTTPStatus
import logging
from uuid import UUID

from tornado import httputil
from tornado.web import HTTPError as TornadoHTTPError, MissingArgumentError, RequestHandler

from pokerserver.database import UUIDsRelation
from pokerserver.models import Match, Player, Table, TableNotFoundError

LOG = logging.getLogger(__name__)


class BaseController(RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player_name = None
        self.player = None

    async def prepare(self):
        await self.authenticate()

    def is_authenticated(self):
        return self.player_name is not None

    async def authenticate(self):
        uuid = self._get_uuid()
        uuid_data = await UUIDsRelation.load_by_uuid(uuid)
        if uuid_data is not None:
            self.player_name = uuid_data['player_name']
            self.player = await Player.load_if_exists(self.player_name)
            LOG.info("[%s] Authenticated", self.player_name)

    def _get_uuid(self):
        try:
            return UUID(self.get_query_argument('uuid'))
        except MissingArgumentError:
            return None
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid uuid')

    def write_error(self, status_code, **kwargs):
        if 'exc_info' in kwargs:
            exception = kwargs['exc_info'][1]
            standard_message = httputil.responses[status_code]
            if hasattr(exception, 'log_message') and exception.log_message is not None:
                self.set_status(status_code, reason='{} ({})'.format(standard_message, exception.log_message))

        super().write_error(status_code, **kwargs)

    async def load_match(self, table_name):
        try:
            table = await Table.load_by_name(table_name)
        except TableNotFoundError:
            raise HTTPError(HTTPStatus.NOT_FOUND, 'Table not found')
        turn_delay = self.settings.get('args').turn_delay if self.settings.get('args') else 0
        return Match(table, turn_delay)


def authenticated(method):
    @functools.wraps(method)
    async def wrapper(controller, *args):
        if controller.player_name is None:
            raise HTTPError(HTTPStatus.UNAUTHORIZED)
        if asyncio.iscoroutinefunction(method):
            await method(controller, *args)
        else:
            method(controller, *args)

    return wrapper


class HTTPError(TornadoHTTPError):
    def __init__(self, status_code, *args, **kwargs):
        assert isinstance(status_code, HTTPStatus)
        status_code = status_code.value
        super().__init__(status_code, *args, **kwargs)
