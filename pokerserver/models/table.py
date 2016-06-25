from pokerserver.database import TablesRelation

from .player import Player


class Table:
    def __init__(self, id, name, max_player_count, remaining_deck, players, small_blind, big_blind, open_cards,
                 main_pot, side_pots, current_player, dealer, small_blind_player, big_blind_player, is_closed):
        self.id = id
        self.name = name
        self.max_player_count = max_player_count
        self.remaining_deck = remaining_deck
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.open_cards = open_cards
        self.main_pot = main_pot
        self.side_pots = side_pots
        self.current_player = current_player
        self.dealer = dealer
        self.small_blind_player = small_blind_player
        self.big_blind_player = big_blind_player
        self.is_closed = is_closed

    @classmethod
    async def load_all(cls):
        tables = await TablesRelation.load_all()

        players_by_table_id = {}
        for table in tables:
            player = await Player.load_by_table_id(table['id'])
            players_by_table_id[table['id']] = player

        return [cls(**table, players=players_by_table_id[table['id']]) for table in tables]

    @classmethod
    async def load_by_name(cls, name):
        table_data = await TablesRelation.load_table_by_name(name)
        players = await Player.load_by_table_id(table_data['id'])
        return cls(**table_data, players=players)

    @classmethod
    async def create_tables(cls, number, max_player_count):
        table_names = await cls._get_unused_table_names(number)
        for name in table_names:
            await TablesRelation.create_table(name, max_player_count, [])

    def is_free(self):
        return len(self.players) < self.max_player_count

    def to_dict(self, player):
        result = {
            'players': [player.to_dict() for player in self.players],
            'smallBlind': self.small_blind,
            'bigBlind': self.big_blind,
            'openCards': self.open_cards,
            'mainPot': self.main_pot,
            'sidePots': self.side_pots,
            'currentPlayer': self.current_player,
            'dealer': self.dealer,
            'isClosed': self.is_closed
        }

        if player is not None:
            pass

        return result

    def to_dict_for_info(self):
        return {
            'name': self.name,
            'max_player_count': self.max_player_count,
            'players': [player.name for player in self.players]
        }

    @classmethod
    async def _get_unused_table_names(cls, number):
        tables = await cls.load_all()
        used_names = {table.name for table in tables}
        found_names = []
        i = 1
        while len(found_names) < number:
            name = 'Table {}'.format(i)
            if name not in used_names:
                found_names.append(name)
            i += 1

        return found_names
