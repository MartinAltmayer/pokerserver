from argparse import ArgumentParser
import urllib.request
from urllib.error import HTTPError
import json as mod_json
from http import HTTPStatus
import time

POLL_INTERVAL = 1


class TableInfo:
    def __init__(self, name, min_player_count, max_player_count, players):
        self.name = name
        self.min_player_count = min_player_count
        self.max_player_count = max_player_count
        self.players = {int(position): name for position, name in players.items()}

    def is_free_for(self, player_name):
        return len(self.players) < self.max_player_count and player_name not in self.players.values()

    def find_free_position(self):
        for position in range(1, self.max_player_count + 1):
            if position not in self.players:
                return position
        else:
            raise ValueError("No free position found")


class Table:
    def __init__(self, name, current_player, **_):
        self.name = name
        self.current_player = current_player


class Client:
    def __init__(self, host, port, player_name, uuid):
        self.host = host
        self.port = port
        self.player_name = player_name
        self.uuid = uuid

    def play(self):
        self.ensure_uuid()
        table_info, position = self.join()

        while True:
            table = self.fetch_table(table_info.name)
            if table.current_player == self.player_name:
                self.make_turn(table, position)
            time.sleep(POLL_INTERVAL)

    def make_turn(self, table, position):  # pylint: disable=unused-argument
        self.log("It's my turn")

    def ensure_uuid(self):
        if self.uuid is None:
            self.uuid = self._fetch('/uuid?player_name=' + self.player_name, json=False)
            self.log("Received UUID: {}".format(self.uuid))

    def fetch_table(self, name):
        response = self._fetch('/table/{}'.format(name))
        return Table(name, **response)

    def fetch_tables(self):
        response = self._fetch('/tables')
        return [TableInfo(**table_data) for table_data in response['tables']]

    def find_free_table(self, tables):
        for table in tables:
            if table.is_free_for(self.player_name):
                return table
        else:
            raise RuntimeError('No free table')

    def join(self):
        while True:
            tables = self.fetch_tables()
            free_table = self.find_free_table(tables)
            free_position = free_table.find_free_position()

            self.log("Joining {} at {}...".format(free_table.name, free_position))
            try:
                self._fetch('/table/{}/join?player_name={}&position={}&uuid={}'.format(
                    free_table.name, self.player_name, free_position, self.uuid))
                return free_table, free_position
            except HTTPError as error:
                if error.code != HTTPStatus.CONFLICT.value:
                    raise
                # else continue

    def _fetch(self, url, json=True):
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

    def log(self, message):
        print('[{}] {}'.format(self.player_name, message))


def main():
    parser = ArgumentParser(
        description='Simple client for our Python workshop at TNG Technology Consulting.'
    )
    parser.add_argument('-p', '--port', type=int, help='Server port number', default=5555)
    parser.add_argument('-s', '--host', help='Server address', default='localhost')
    parser.add_argument('-u', '--uuid', help='UUID of the player', default=None)
    parser.add_argument(help='Player name', dest='name')
    args = parser.parse_args()

    client = Client(args.host, args.port, args.name, args.uuid)
    client.play()


if __name__ == "__main__":
    main()
