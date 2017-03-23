from enum import Enum

import requests
from requests import HTTPError, Session
from requests.adapters import HTTPAdapter


class RequestError(BaseException):
    pass


class TableInfo:
    def __init__(self, name, min_player_count, max_player_count, players, state):  # pylint: disable=too-many-arguments
        self.name = name
        self.min_player_count = min_player_count
        self.max_player_count = max_player_count
        self.players = {int(position): name for position, name in players.items()}
        self.state = TableState(state)

    @property
    def is_closed(self):
        return self.state is TableState.CLOSED

    def is_free_for(self, player_name):
        return len(self.players) < self.max_player_count and player_name not in self.players.values()

    def find_free_positions(self):
        return [position for position in range(1, self.max_player_count + 1) if position not in self.players]

    def find_free_position(self):
        positions = self.find_free_positions()
        if positions:
            return positions[0]
        else:
            raise ValueError("No free position found")


class Table:
    def __init__(self, name, current_player, players, **kwargs):
        self.name = name
        self.current_player = current_player
        self.players = [Player(**player_dict) for player_dict in players]
        self.players.sort(key=lambda p: p.position)
        self.round = kwargs.get('round')
        self.pots = [Pot(**pot_dict) for pot_dict in kwargs.get('pots', [])]
        self.open_cards = kwargs.get('open_cards')
        self.state = TableState(kwargs.get('state', 'closed'))

    def __eq__(self, other):
        return isinstance(other, Table) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not isinstance(other, Table) or self.__dict__ != other.__dict__

    @property
    def is_closed(self):
        return self.state is TableState.CLOSED


class TableState(Enum):
    WAITING_FOR_PLAYERS = 'waiting for players'
    RUNNING_GAME = 'running game'
    CLOSED = 'closed'


class Pot:
    def __init__(self, bets=None):
        self.bets = bets or {}

    @property
    def amount(self):
        return sum(self.bets.values(), 0)

    def __eq__(self, other):
        return self.bets == other.bets

    def __ne__(self, other):
        return self.bets != other.bets


class Player:
    def __init__(self, name, position, balance, bet, cards, state, table_id):
        # pylint: disable=too-many-arguments
        self.name = name
        self.position = int(position)
        self.balance = int(balance)
        self.bet = int(bet)
        self.cards = cards
        self.state = PlayerState(state)
        self.table_id = int(table_id)

    def __eq__(self, other):
        return isinstance(other, Player) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not isinstance(other, Player) or self.__dict__ != other.__dict__


class PlayerState(Enum):
    PLAYING = 'playing'
    FOLDED = 'folded'
    ALL_IN = 'all in'
    SITTING_OUT = 'sitting out'


class BaseClient:
    def __init__(self, host, port, log_requests=False):
        self.host = host
        self.port = port
        self.log_requests = log_requests
        self.session = Session()
        self.session.mount('http://', HTTPAdapter(max_retries=3))

    def receive_uuid(self, player_name):
        try:
            response = self.post('/uuid', json={'player_name': player_name})
            return response.text
        except RequestError:
            return None

    def fetch_table(self, name, uuid=None):
        if uuid:
            response = self.fetch('/table/{}?uuid={}'.format(name, uuid))
        else:
            response = self.fetch('/table/{}'.format(name))
        return Table(name, **response)

    def fetch_tables(self):
        response = self.fetch('/tables')
        return [TableInfo(**table_data) for table_data in response['tables']]

    @staticmethod
    def find_free_table(table_infos, *player_names):
        for table in table_infos:
            if table.is_closed:
                continue
            if (len(table.find_free_positions()) >= len(player_names) and
                all(table.is_free_for(name) for name in player_names)):
                return table
        else:
            raise RuntimeError('No free table')

    def join_table(self, table_info, position, uuid):
        self.post(
            '/table/{}/actions/join?uuid={}'.format(table_info.name, uuid),
            json={'position': position}
        )

    def fold(self, table_name, uuid):
        url = '/table/{}/actions/fold?uuid={}'.format(table_name, uuid)
        self.post(url)

    def check(self, table_name, uuid):
        url = '/table/{}/actions/check?uuid={}'.format(table_name, uuid)
        self.post(url)

    def call(self, table_name, uuid):
        url = '/table/{}/actions/call?uuid={}'.format(table_name, uuid)
        self.post(url)

    def raise_bet(self, table_name, uuid, amount):
        self.post('/table/{}/actions/raise?uuid={}'.format(table_name, uuid), json={'amount': amount})

    def post(self, url, **kwargs):
        url = self.build_url(url)
        if self.log_requests:
            self.log("POST {}... ".format(url), new_line=False)
        try:
            response = self.session.post(url, **kwargs)
            response.raise_for_status()
            if self.log_requests:
                self.log('{}'.format(response.status_code))
        except HTTPError as error:
            self.log('{}'.format(error.response.status_code))
            raise RequestError
        except requests.ConnectionError:
            self.log('ConnectionError')
            raise RequestError
        return response

    def fetch(self, url, as_json=True):
        url = self.build_url(url)
        if self.log_requests:
            self.log("GET {}... ".format(url), new_line=False)
        try:
            response = self.session.get(url)
            response.raise_for_status()
            if self.log_requests:
                self.log('{}'.format(response.status_code))
        except HTTPError as error:
            self.log('{}'.format(error.response.status_code))
            raise RequestError
        except requests.ConnectionError:
            self.log('ConnectionError')
            raise RequestError

        return response.json() if as_json else response.text

    def build_url(self, url):
        url = 'http://{}:{}{}'.format(self.host, self.port, url)
        return url

    def log(self, message, new_line=True):  # pylint: disable=no-self-use
        print(message, end='\n' if new_line else '')
