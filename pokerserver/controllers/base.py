import asyncio
import functools
from uuid import UUID

from http import HTTPStatus
import logging
from tornado.web import RequestHandler, MissingArgumentError, HTTPError

from pokerserver.database.uuids import UUIDsRelation
from pokerserver.models.player import Player

LOG = logging.getLogger(__name__)


class BaseController(RequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.player_name = None
        self.player = None

    def is_authenticated(self):
        return self.player_name is not None

    async def authenticate(self):
        uuid = self._get_uuid()
        uuid_data = await UUIDsRelation.load_by_uuid(uuid)
        if uuid_data is None:
            raise HTTPError(HTTPStatus.UNAUTHORIZED)

        self.player_name = uuid_data['player_name']
        self.player = await Player.load_if_exists(self.player_name)
        LOG.info("Authenticated:", self.player_name, self.player)

    def _get_uuid(self):
        try:
            return UUID(self.get_query_argument('uuid'))  # TODO: should not be included in url
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.UNAUTHORIZED)
        except ValueError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid uuid')


def authenticated(method):
    @functools.wraps(method)
    async def wrapper(controller, *args):
        await controller.authenticate()
        if asyncio.iscoroutinefunction(method):
            await method(controller, *args)
        else:
            method(controller, *args)

    return wrapper
