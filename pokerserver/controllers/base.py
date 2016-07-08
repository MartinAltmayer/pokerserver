import asyncio
import functools
from uuid import UUID

from http import HTTPStatus
import logging
from tornado.web import RequestHandler, MissingArgumentError, HTTPError

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models.match import Match
from pokerserver.models.player import Player
from pokerserver.models.table import Table, TableNotFoundError

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
            LOG.info("Authenticated %s", self.player_name)

    def _get_uuid(self):
        try:
            return UUID(self.get_query_argument('uuid'))
        except MissingArgumentError:
            return None
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid uuid')

    @classmethod
    async def load_match(cls, table_name):
        try:
            table = await Table.load_by_name(table_name)
        except TableNotFoundError:
            raise HTTPError(HTTPStatus.NOT_FOUND, 'Table not found')
        return Match(table)


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
