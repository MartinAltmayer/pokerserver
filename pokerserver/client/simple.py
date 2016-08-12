from urllib.error import HTTPError
from http import HTTPStatus
import time

from pokerserver.client import BaseClient

POLL_INTERVAL = 1


class SimpleClient(BaseClient):
    def __init__(self, host, port, player_name, uuid):
        super().__init__(host, port)
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
            self.uuid = self.receive_uuid(self.player_name)
            self.log("Received UUID: {}".format(self.uuid))

    def join(self):
        while True:
            tables = self.fetch_tables()
            free_table = self.find_free_table(tables, self.player_name)
            free_position = free_table.find_free_position()

            self.log("Joining {} at {}...".format(free_table.name, free_position))
            try:
                self.join_table(free_table, self.player_name, free_position, self.uuid)
                return free_table, free_position
            except HTTPError as error:
                if error.code != HTTPStatus.CONFLICT.value:
                    raise
                # else continue

    def log(self, message):
        super().log('[{}] {}'.format(self.player_name, message))
