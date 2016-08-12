import urllib.request
from urllib.error import HTTPError
import json as mod_json

POLL_INTERVAL = 1


class TableInfo:
    def __init__(self, name, min_player_count, max_player_count, players):
        self.name = name
        self.min_player_count = min_player_count
        self.max_player_count = max_player_count
        self.players = {int(position): name for position, name in players.items()}

    def is_free_for(self, player_name):
        return len(self.players) < self.max_player_count and player_name not in self.players.values()

    def find_free_positions(self):
        return [position for position in range(1, self.max_player_count + 1)
                if position not in self.players]

    def find_free_position(self):
        positions = self.find_free_positions()
        if len(positions) > 0:
            return positions[0]
        else:
            raise ValueError("No free position found")


class Table:
    def __init__(self, name, current_player, players, **_):
        self.name = name
        self.current_player = current_player
        self.players = [Player(**player_data) for player_data in players]
        self.players.sort(key=lambda p: p.position)


class Player:
    def __init__(self, name, position, balance, bet, cards, has_folded, table_id):
        # pylint: disable=too-many-arguments
        self.name = name
        self.position = int(position)
        self.balance = int(balance)
        self.bet = int(bet)
        self.cards = cards
        self.has_folded = bool(has_folded)
        self.table_id = int(table_id)


class BaseClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def receive_uuid(self, player_name):
        return self.fetch('/uuid?player_name=' + player_name, json=False)

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
    def find_free_table(tables, *player_names):
        for table in tables:
            if (len(table.find_free_positions()) >= len(player_names) and
                    all(table.is_free_for(name) for name in player_names)):
                return table
        else:
            raise RuntimeError('No free table')

    def join_table(self, table, player_name, position, uuid):
        self.fetch('/table/{}/join?player_name={}&position={}&uuid={}'.format(
            table.name, player_name, position, uuid))

    def fetch(self, url, json=True):
        url = 'http://{}:{}{}'.format(self.host, self.port, url)
        self.log("Fetching from {}... ".format(url))
        try:
            response = urllib.request.urlopen(url)
            self.log('...{}'.format(response.code))
        except HTTPError as error:
            self.log('...{}'.format(error.code))
            raise

        data = response.read()
        if not data:
            return None
        data = data.decode('utf-8')
        if json:
            return mod_json.loads(data)
        else:
            return data

    def log(self, message):  # pylint: disable=no-self-use
        print(message)
