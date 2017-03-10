import re
import uuid as mod_uuid
from http import HTTPStatus

from tornado.web import MissingArgumentError

from pokerserver.database import DuplicateKeyError, UUIDsRelation
from pokerserver.models import PLAYER_NAME_PATTERN
from .base import BaseController, HTTPError


class UUIDController(BaseController):
    route = r'/uuid/?'

    async def get(self):
        player_name = self._get_player_name()
        uuid = mod_uuid.uuid4()
        try:
            await UUIDsRelation.add_uuid(uuid, player_name)
        except DuplicateKeyError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Player already registered')
        self.write(str(uuid))

    def _get_player_name(self):
        try:
            player_name = self.get_query_argument('player_name')
        except MissingArgumentError:
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Missing parameter: "player_name"')
        if not re.match(PLAYER_NAME_PATTERN, player_name):
            raise HTTPError(HTTPStatus.BAD_REQUEST, 'Invalid player name')

        return player_name
