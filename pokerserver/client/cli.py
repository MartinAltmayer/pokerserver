from time import sleep

from pokerserver.client import BaseClient, RequestError


class CliClient(BaseClient):
    INTERVAL = 1

    def __init__(self, host, port, player_count, log_requests=False):
        super().__init__(host, port, log_requests=log_requests)
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
                try:
                    table = self.load_table_and_players()
                except RequestError:
                    sleep(1)
                    continue

                if table != self.table:
                    self.table = table
                    self.print_table_info()
                    self.print_player_info()

                if self.table.current_player in self.player_names:
                    self.read_and_execute_command()
                else:
                    sleep(self.INTERVAL)
        except EOFError:
            print()

    def register_players(self, number):
        index = 0
        self.player_names = []
        self.uuids = {}
        while len(self.player_names) < number:
            index += 1
            name = 'Player{}'.format(index)
            uuid = self.receive_uuid(name)
            if uuid is None:
                continue  # player exists

            self.player_names.append(name)
            self.uuids[name] = uuid

    def find_table_and_join(self):
        table = self.find_suitable_table()
        for name, position in zip(self.player_names, table.find_free_positions()):
            self.join_table(table, position, self.uuids[name])
        self.table_name = table.name  # table is a TableInfo, full data is loaded later

    def find_suitable_table(self):
        tables = self.fetch_tables()
        for table in tables:
            if len(table.players) + len(self.player_names) <= table.max_player_count:
                return table
        else:
            raise RuntimeError('No suitable table')

    def load_table_and_players(self):
        table = self.fetch_table(self.table_name)
        # Load the same table separately for each player to get the cards.
        # Insert the cards in the table above.
        for player in table.players:
            uuid = self.uuids.get(player.name)
            if uuid is not None:
                table_viewed_by_player = self.fetch_table(self.table_name, uuid)
                player.cards = self.find_player_cards(table_viewed_by_player, player)
        return table

    @staticmethod
    def find_player_cards(table, player):
        for pla in table.players:
            if pla.name == player.name:
                return pla.cards
        else:
            return []

    def read_and_execute_command(self):
        try:
            command_text = input('{}> '.format(self.table.current_player))
            uuid = self.uuids[self.table.current_player]
            self.execute_command(command_text, uuid)
        except ValueError:
            print('Invalid command. Enter one of fold, call, check, raise <amount>')

    @property
    def players(self):
        return self.table.players

    def print_table_info(self):
        pots = ', '.join([str(pot.amount) for pot in self.table.pots]) or 'None'
        open_cards = ' '.join(self.table.open_cards or [])
        print('{} Pots: {} | Cards: {}'.format(self.table.round.upper(), pots, open_cards))

    def print_player_info(self):
        parts = []
        for player in self.players:
            current = ' [*]' if player.name == self.table.current_player else ''
            if player.name in self.player_names:
                parts.append('{}{}: {}, {}, {}'.format(player.name, current, player.balance, player.bet, player.cards))
            else:
                parts.append('({}){}: {}, {}'.format(player.name, current, player.balance, player.bet))
        print('  |  '.join(parts))

    def execute_command(self, string, uuid):
        try:
            parts = string.split()
            name = parts[0]
            if name not in ['fold', 'call', 'check', 'raise']:
                raise ValueError('Invalid command')
            try:
                if name == 'raise':
                    self.raise_bet(self.table.name, uuid, int(parts[1]))
                else:
                    getattr(self, name)(self.table.name, uuid)
            except RequestError:
                pass  # let's poll until the server works again
        except IndexError:
            raise ValueError('Missing part')
