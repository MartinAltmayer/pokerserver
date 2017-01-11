from urllib.error import HTTPError

from http import HTTPStatus

from pokerserver.client import BaseClient


class CliClient(BaseClient):
    def __init__(self, host, port, player_count):
        super().__init__(host, port)
        self.player_count = player_count
        self.player_names = []
        self.table_name = None
        self.table = None
        self.uuids = {}

    def run(self):
        self.register_players(self.player_count)
        self.find_table_and_join()
        try:
            while True:
                self.load_table_and_players()
                self.print_table_info()
                self.print_player_info()
                self.read_and_send_command()
        except EOFError:
            print()

    def register_players(self, number):
        index = 0
        self.player_names = []
        self.uuids = {}
        while len(self.player_names) < number:
            index += 1
            name = 'Player{}'.format(index)
            try:
                uuid = self.receive_uuid(name)
            except HTTPError as exc:
                if exc.code == HTTPStatus.BAD_REQUEST.value:
                    continue  # player exists
                else:
                    raise

            self.player_names.append(name)
            self.uuids[name] = uuid

    def find_table_and_join(self):
        table = self.find_suitable_table()
        for name, position in zip(self.player_names, table.find_free_positions()):
            self.join_table(table, name, position, self.uuids[name])
        self.table_name = table.name  # table is a TableInfo, full data is loaded later

    def find_suitable_table(self):
        tables = self.fetch_tables()
        for table in tables:
            if not table.players and table.min_player_count <= len(self.player_names) <= table.max_player_count:
                return table
        else:
            raise RuntimeError('No suitable table')

    def load_table_and_players(self):
        self.table = self.fetch_table(self.table_name)
        # Load the same table separately for each player to get the cards.
        # Insert the cards in the table above.
        for player in self.players:
            table_viewed_by_player = self.fetch_table(self.table_name, self.uuids[player.name])
            player.cards = self.find_player_cards(table_viewed_by_player, player)

    @staticmethod
    def find_player_cards(table, player):
        for pla in table.players:
            if pla.name == player.name:
                return pla.cards
        else:
            return []

    def read_and_send_command(self):
        command = None
        while True:
            try:
                command_text = input('{}> '.format(self.table.current_player))
                command = Command.parse(command_text)
                break
            except ValueError:
                print('Invalid command. Enter one of fold, call, check, raise <amount>')

        uuid = self.uuids[self.table.current_player]
        try:
            if command.argument_name is None:
                self.fetch('/table/{}/{}?uuid={}'.format(self.table.name, command.name, uuid))
            else:
                self.fetch('/table/{}/{}?uuid={}&{}={}'.format(self.table.name, command.name, uuid,
                                                               command.argument_name, command.argument))
        except HTTPError as exc:
            print(exc)

    @property
    def players(self):
        return self.table.players

    def print_table_info(self):
        print('{} Pot: {} | Cards: {}'.format(self.table.round.upper(), self.table.main_pot, self.table.open_cards))

    def print_player_info(self):
        parts = []
        for player in self.players:
            current = ' (*)' if player.name == self.table.current_player else ''
            parts.append('{}{}: {}, {}, {}'.format(player.name, current, player.balance, player.bet, player.cards))
        print('  |  '.join(parts))


class Command:
    def __init__(self, name, argument=None):
        if name not in ['fold', 'call', 'check', 'raise']:
            raise ValueError('Invalid command')
        self.name = name
        self.argument = argument

    @property
    def argument_name(self):
        return 'amount' if self.name == 'raise' else None

    @classmethod
    def parse(cls, string):
        try:
            parts = string.split()
            name = parts[0]
            if name == 'raise':
                argument = int(parts[1])
            else:
                argument = None
            return cls(name, argument)
        except IndexError:
            raise ValueError('Missing part')
