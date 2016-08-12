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


class BaseClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port

    def receive_uuid(self, player_name):
        return self.fetch('/uuid?player_name=' + player_name, json=False)

    def fetch_table(self, name):
        response = self.fetch('/table/{}'.format(name))
        return Table(name, **response)

    def fetch_tables(self):
        response = self.fetch('/tables')
        return [TableInfo(**table_data) for table_data in response['tables']]

    def find_free_table(self, tables, player_name):
        for table in tables:
            if table.is_free_for(player_name):
                return table
        else:
            raise RuntimeError('No free table')

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

    def log(self, message):
        print(message)
