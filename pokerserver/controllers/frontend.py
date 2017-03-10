from http import HTTPStatus
from urllib.parse import quote
from tornado.web import RequestHandler, HTTPError

from pokerserver.database import PlayerState
from pokerserver.models import Table, TableNotFoundError

TABLE_NAME_PATTERN = r'(.+)'


class IndexController(RequestHandler):
    route = r'/gui/' + TABLE_NAME_PATTERN

    async def get(self, table_name):
        data_url = 'http://{}/fedata/{}'.format(self.request.host, quote(table_name))
        self.write(HTML.format(data_url=data_url))


HTML = """<!doctype html>
<html>
  <head>
    <link rel="stylesheet" href="/static/style.css" type="text/css" />
    <script>window.DATA_URL = '{data_url}';</script>
  </head>
  <body>
    <div class="app"></div>
    <script src="/static/client-bundle.js"></script>
  </body>
</html>"""


class FrontendDataController(RequestHandler):
    route = r'/fedata/' + TABLE_NAME_PATTERN

    async def get(self, table_name):
        try:
            table = await Table.load_by_name(table_name)
        except TableNotFoundError:
            raise HTTPError(HTTPStatus.NOT_FOUND)

        self.write({
            'players': [self.write_player(table, player) for player in table.players],
            'openCards': table.open_cards
        })

    @staticmethod
    def write_player(table, player):
        return {
            'position': player.position,
            'name': player.name,
            'balance': player.balance,
            'bet': player.bet,
            'dealer': player is table.dealer,
            'current': player is table.current_player,
            'folded': player.state is PlayerState.FOLDED,
            'cards': player.cards
        }


class DevCookieController(RequestHandler):
    route =r'/devcookie'

    async def get(self):
        provided_password = self.get_argument('password', '')
        actual_password = self.application.settings['args'].password
        if not actual_password:
            raise HTTPError(HTTPStatus.NOT_FOUND)

        if provided_password != actual_password:
            raise HTTPError(HTTPStatus.BAD_REQUEST)

        self.set_cookie('devcookie', actual_password)
        self.set_status(HTTPStatus.NO_CONTENT)
