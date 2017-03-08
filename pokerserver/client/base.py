from enum import Enum
import json
from urllib.error import HTTPError
from urllib.request import urlopen


class TableInfo:
    def __init__(self, name, min_player_count, max_player_count, players):
        self.name = name
        self.min_player_count = min_player_count
        self.max_player_count = max_player_count
        self.players = {int(position): name for position, name in players.items()}

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


class Pot:
    def __init__(self, bets=None):
        self.bets = bets or {}

    @property
    def amount(self):
        return sum(self.bets.values(), 0)


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


class PlayerState(Enum):
    PLAYING = 'playing'
    FOLDED = 'folded'
    ALL_IN = 'all in'
    SITTING_OUT = 'sitting out'


class BaseClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def receive_uuid(self, player_name):
        return self.fetch('/uuid?player_name=' + player_name, as_json=False)

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
            if (len(table.find_free_positions()) >= len(player_names) and
                    all(table.is_free_for(name) for name in player_names)):
                return table
        else:
            raise RuntimeError('No free table')

    def join_table(self, table_info, player_name, position, uuid):
        self.fetch(
            '/table/{}/join?player_name={}&position={}&uuid={}'.format(
                table_info.name,
                player_name,
                position,
                uuid
            )
        )

    def fetch(self, url, as_json=True):
        url = 'http://{}:{}{}'.format(self.host, self.port, url)
        self.log("Fetching from {}... ".format(url), new_line=False)
        try:
            response = urlopen(url)
            self.log('{}'.format(response.code))
        except HTTPError as error:
            self.log('{}'.format(error.code))
            raise

        data = response.read()
        if not data:
            return None
        data = data.decode('utf-8')

        return json.loads(data) if as_json else data

    def log(self, message, new_line=True):  # pylint: disable=no-self-use
        print(message, end='\n' if new_line else '')
