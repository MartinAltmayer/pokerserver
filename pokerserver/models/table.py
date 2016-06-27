from pokerserver.database import TablesRelation

from .player import Player


class TableNotFoundError(Exception):
    pass


# pylint: disable=too-many-instance-attributes
class Table:
    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(self, table_id, name, max_player_count, remaining_deck, players, small_blind, big_blind, open_cards,
                 main_pot, side_pots, current_player, dealer, small_blind_player, big_blind_player, is_closed):
        self.table_id = table_id
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
            player = await Player.load_by_table_id(table['table_id'])
            players_by_table_id[table['table_id']] = player

        return [cls(**table, players=players_by_table_id[table['table_id']]) for table in tables]

    @classmethod
    async def load_by_name(cls, name):
        table_data = await TablesRelation.load_table_by_name(name)
        if table_data is None:
            raise TableNotFoundError()

        players = await Player.load_by_table_id(table_data['table_id'])
        return cls(**table_data, players=players)

    @classmethod
    async def create_tables(cls, number, max_player_count, small_blind, big_blind):
        table_ids_and_names = await cls._get_unused_table_names_and_ids(number)
        for table_id, table_name in table_ids_and_names:
            await TablesRelation.create_table(
                table_id,
                table_name,
                max_player_count,
                '',
                small_blind,
                big_blind,
                '',
                0,
                '',
                None,
                None,
                None,
                None,
                False
            )

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
    async def _get_unused_table_names_and_ids(cls, number):
        tables = await cls.load_all()
        used_names = {table.name for table in tables}
        used_ids = {table.table_id for table in tables}
        found_names = []
        found_ids = []
        i = 1
        while len(found_names) < number:
            name = 'Table{}'.format(i)
            if name not in used_names:
                found_names.append(name)
            i += 1

        test_id = 1
        while len(found_ids) < number:
            if test_id not in used_ids:
                found_ids.append(test_id)
            test_id += 1

        return zip(found_ids, found_names)
