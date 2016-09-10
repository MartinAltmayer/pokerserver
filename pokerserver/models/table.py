from enum import Enum

from pokerserver.database import TablesRelation
from .player import Player


class TableNotFoundError(Exception):
    pass


class Round(Enum):
    preflop = 1
    flop = 2
    turn = 3
    river = 4


# pylint: disable=too-many-instance-attributes
class Table:
    # pylint: disable=too-many-arguments, too-many-locals
    def __init__(self, table_id, name, config, players=None, remaining_deck=None,
                 open_cards=None, main_pot=0, side_pots=None, current_player=None, dealer=None,
                 small_blind_player=None, big_blind_player=None, highest_bet_player=None, is_closed=False):
        self.table_id = table_id
        self.name = name
        self.config = config
        self.remaining_deck = remaining_deck or []
        self.players = players or []
        self.open_cards = open_cards or []
        self.main_pot = main_pot
        self.side_pots = side_pots or []
        self.current_player = current_player
        self.dealer = dealer
        self.small_blind_player = small_blind_player
        self.big_blind_player = big_blind_player
        self.highest_bet_player = highest_bet_player
        self.is_closed = is_closed

    @classmethod
    async def load_all(cls):
        tables = await TablesRelation.load_all()

        players_by_table_id = {}
        for table in tables:
            players = await Player.load_by_table_id(table['table_id'])
            players_by_table_id[table['table_id']] = players

        return [cls(**table, players=players_by_table_id[table['table_id']]) for table in tables]

    @classmethod
    async def load_by_name(cls, name):
        table_data = await TablesRelation.load_table_by_name(name)
        if table_data is None:
            raise TableNotFoundError()

        players = await Player.load_by_table_id(table_data['table_id'])
        for player_attribute in ['dealer', 'small_blind_player', 'big_blind_player', 'current_player',
                                 'highest_bet_player']:
            if table_data[player_attribute] is not None:
                for player in players:
                    if player.name == table_data[player_attribute]:
                        table_data[player_attribute] = player
                        break
                else:
                    raise ValueError("Cannot find player '{}'".format(table_data[player_attribute]))
        return cls(**table_data, players=players)

    @classmethod
    async def create_tables(cls, number, table_config):
        table_ids_and_names = await cls._get_unused_table_names_and_ids(number)
        for table_id, table_name in table_ids_and_names:
            await TablesRelation.create_table(
                table_id=table_id, name=table_name, config=table_config, remaining_deck=[], open_cards=[],
                main_pot=0, side_pots=[], current_player=None, dealer=None,
                small_blind_player=None, big_blind_player=None, highest_bet_player=None, is_closed=False
            )

    def to_dict(self, player_name):
        player_names = {player.name for player in self.players}
        result = {
            'players': [player.to_dict(show_cards=player_name == player.name) for player in self.players],
            'small_blind': self.config.small_blind,
            'big_blind': self.config.big_blind,
            'round': self.round.name,
            'open_cards': self.open_cards,
            'main_pot': self.main_pot,
            'side_pots': self.side_pots,
            'current_player': self.current_player.name if self.current_player else None,
            'dealer': self.dealer.name if self.dealer else None,
            'is_closed': self.is_closed,
            'can_join': player_name not in player_names and len(self.players) < self.config.max_player_count
        }

        return result

    def to_dict_for_info(self):
        return {
            'name': self.name,
            'min_player_count': self.config.min_player_count,
            'max_player_count': self.config.max_player_count,
            'players': {player.position: player.name for player in self.players}
        }

    @property
    def round(self):
        return {
            0: Round.preflop,
            3: Round.flop,
            4: Round.turn,
            5: Round.river
        }[len(self.open_cards)]

    def is_free(self):
        return len(self.players) < self.config.max_player_count

    def is_position_valid(self, position):
        return 1 <= position <= self.config.max_player_count

    def is_position_free(self, position):
        return self.is_position_valid(position) and self.get_player_at(position) is None

    def get_player_at(self, position):
        for player in self.players:
            if player.position == position:
                return player
        else:
            return None

    def find_player(self, name):
        for player in self.players:
            if player.name == name:
                return player
        else:
            raise ValueError("Player '{}' not found".format(name))

    def is_player_at_table(self, player_name):
        return any(player.name == player_name for player in self.players)

    def active_players(self):
        return [player for player in self.players if not player.has_folded]

    def players_between(self, player1, player2):
        def sorted_by_position(players):
            players.sort(key=lambda p: p.position)
            return players

        if player1 == player2:
            return [player1]
        if player1.position < player2.position:
            return sorted_by_position(
                [p for p in self.players if player1.position <= p.position <= player2.position])
        else:
            section1 = sorted_by_position([p for p in self.players if p.position >= player1.position])
            section2 = sorted_by_position([p for p in self.players if p.position <= player2.position])
            return section1 + section2

    def player_left_of(self, player, player_filter=None):
        players = player_filter if player_filter is not None else self.players
        players = [p for p in players if p != player]
        if len(players) == 0:
            raise ValueError('No player left of {}'.format(player.name))
        players.sort(key=lambda p: (p.position <= player.position, p.position))
        return players[0]

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

    async def set_special_players(self, **kwargs):
        assert set(kwargs.keys()) <= {
            'dealer', 'small_blind_player', 'big_blind_player', 'current_player', 'highest_bet_player'}
        self.__dict__.update(kwargs)
        updates = {key: player.name if player is not None else None for key, player in kwargs.items()}
        await TablesRelation.set_special_players(self.table_id, **updates)

    async def set_current_player(self, current_player):
        await TablesRelation.set_special_players(
            self.table_id, current_player=current_player.name if current_player else None)

    async def set_cards(self, remaining_deck=None, open_cards=None):
        if remaining_deck is not None:
            self.remaining_deck = remaining_deck
        if open_cards is not None:
            self.open_cards = open_cards

        await TablesRelation.set_cards(
            self.table_id, remaining_deck=self.remaining_deck, open_cards=self.open_cards)

    async def check_and_unset_current_player(self, player_name):
        return await TablesRelation.check_and_unset_current_player(self.table_id, player_name)

    async def set_pot(self, amount):
        await TablesRelation.set_pot(self.table_id, amount)

    async def increase_pot(self, amount):
        await TablesRelation.set_pot(self.table_id, self.main_pot + amount)
