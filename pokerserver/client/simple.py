from http import HTTPStatus
from random import choice
import time

from requests import HTTPError

from pokerserver.client import BaseClient

POLL_INTERVAL_SECONDS = 1


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
            time.sleep(POLL_INTERVAL_SECONDS)

    def make_turn(self, table, position):  # pylint: disable=unused-argument
        self.log("It's my turn")
        if self.can_check(table, position):
            self.check(table.name, self.uuid)
            return

        actions = {
            'fold': lambda: self.fold(table.name, self.uuid),
            'call': lambda: self.call(table.name, self.uuid),
            'raise': lambda: self.raise_bet(table.name, self.uuid, 3 * self.maximum_bet(table, position))
        }
        action = choice(list(actions.keys()))
        actions[action]()

    @classmethod
    def can_check(cls, table, position):
        my_bet = next(player.bet for player in table.players if player.position == position)
        maximum_bet = cls.maximum_bet(table, position)
        return my_bet >= maximum_bet

    @staticmethod
    def maximum_bet(table, position):
        return max((player.bet for player in table.players if player.position != position))

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
                self.join_table(free_table, free_position, self.uuid)
                return free_table, free_position
            except HTTPError as error:
                if error.response.status_code != HTTPStatus.CONFLICT.value:
                    raise

    def log(self, message, new_line=True):
        super().log('[{}] {}'.format(self.player_name, message), new_line=new_line)
