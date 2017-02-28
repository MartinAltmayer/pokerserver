from asyncio import gather
from enum import Enum, unique

from pokerserver.database import PlayerState, PlayersRelation, TablesRelation
from .player import Player


class TableNotFoundError(Exception):
    pass


@unique
class Round(Enum):
    preflop = 1
    flop = 2
    turn = 3
    river = 4


# pylint: disable=too-many-instance-attributes, too-many-public-methods
class Table:
    # pylint: disable=too-many-arguments, too-many-locals, unused-argument
    def __init__(self, table_id, name, config, players=None, remaining_deck=None,
                 open_cards=None, pots=None, current_player=None, current_player_token=None,
                 dealer=None, is_closed=False, joined_players=None):
        self.table_id = table_id
        self.name = name
        self.config = config
        self.remaining_deck = remaining_deck or []
        self.players = players or []
        self.open_cards = open_cards or []
        self.pots = [Pot(**pot) for pot in pots] if pots else [Pot()]
        self.current_player = current_player
        self.dealer = dealer
        self.is_closed = is_closed
        self.joined_players = joined_players or []

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
        for player_attribute in ['dealer', 'current_player']:
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
                pots=[Pot().to_dict()], current_player=None, current_player_token=None, dealer=None,
                is_closed=False, joined_players=None
            )

    def to_dict(self, player_name):
        player_names = {player.name for player in self.players}
        can_join = (
            player_name not in player_names and
            player_name not in self.joined_players and
            len(self.players) < self.config.max_player_count
        )
        result = {
            'players': [player.to_dict(show_cards=player_name == player.name) for player in self.players],
            'small_blind': self.config.small_blind,
            'big_blind': self.config.big_blind,
            'round': self.round.name,
            'open_cards': self.open_cards,
            'pots': [pot.to_dict() for pot in self.pots],
            'current_player': self.current_player.name if self.current_player else None,
            'dealer': self.dealer.name if self.dealer else None,
            'is_closed': self.is_closed,
            'can_join': can_join
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
        return [player for player in self.players if player.state != PlayerState.FOLDED]

    def player_positions_between(self, pos1, pos2):
        if pos1 == pos2:
            return [pos1]
        all_positions = [player.position for player in self.players]
        if pos1 < pos2:
            return sorted([p for p in all_positions if pos1 <= p <= pos2])
        section1 = sorted([p for p in all_positions if p >= pos1])
        section2 = sorted([p for p in all_positions if p <= pos2])
        return section1 + section2

    def player_left_of(self, player, player_filter=None):
        players = player_filter if player_filter is not None else self.players
        players = [p for p in players if p != player]
        if not players:
            raise ValueError('No player left of {}'.format(player.name))
        players.sort(key=lambda p: (p.position <= player.position, p.position))
        return players[0]

    def player_right_of(self, player, player_filter=None):
        players = player_filter if player_filter is not None else self.players
        players = [p for p in players if p != player]
        if not players:
            raise ValueError('No player right of {}'.format(player.name))
        players.sort(key=lambda p: (p.position > player.position, -p.position))
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

    async def set_dealer(self, dealer):
        self.dealer = dealer
        await TablesRelation.set_dealer(self.table_id, self.dealer.name if self.dealer is not None else None)

    async def set_current_player(self, current_player, token):
        player_name = current_player.name if current_player else None
        self.current_player = self.find_player(player_name)
        await TablesRelation.set_current_player(self.table_id, player_name, token)

    async def set_cards(self, remaining_deck=None, open_cards=None):
        if remaining_deck is not None:
            self.remaining_deck = remaining_deck
        if open_cards is not None:
            self.open_cards = open_cards

        await TablesRelation.set_cards(
            self.table_id, remaining_deck=self.remaining_deck, open_cards=self.open_cards)

    async def check_and_unset_current_player(self, player_name, token=None):
        is_current_player = await TablesRelation.check_and_unset_current_player(
            self.table_id, player_name, token)
        if is_current_player:
            self.current_player = None
        return is_current_player

    async def clear_pots(self):
        self.pots = [Pot()]
        await self._set_pots()

    async def increase_pot(self, position, bet):
        for index, pot in enumerate(self.pots.copy()):
            existing_bet = pot.bet(position)
            max_bet = pot.max_bet if pot.max_bet > 0 else bet
            if bet > 0 and existing_bet <= max_bet:
                required_bet = max_bet - existing_bet
                if bet >= required_bet:
                    pot.add_bet(position, required_bet)
                    bet -= required_bet
                else:
                    pot.add_bet(position, bet)
                    new_pot = pot.split(bet + existing_bet)
                    self.pots.insert(index + 1, new_pot)
                    bet = 0
                    break
        if bet > 0:
            if self.has_all_in_players(self.pots[-1], position):
                self.pots += [Pot()]
            self.pots[-1].add_bet(position, bet)
        await self._set_pots()

    def has_all_in_players(self, pot, excluded_position):
        all_in_positions = {
            player.position
            for player in self.players
            if player.is_all_in() and not player.position == excluded_position
        }
        return len(all_in_positions) > 0 and not all_in_positions.isdisjoint(pot.positions)

    async def _set_pots(self):
        await TablesRelation.set_pots(self.table_id, [pot.to_dict() for pot in self.pots])

    async def add_player(self, player):
        self.players.append(player)
        await TablesRelation.add_joined_player(self.table_id, player.name)

    async def remove_player(self, player):
        self.players.remove(player)
        await PlayersRelation.delete_player(self.table_id, player.position)

    async def draw_cards(self, number):
        assert number <= len(self.remaining_deck)
        self.remaining_deck, cards = self.remaining_deck[:-number], self.remaining_deck[-number:]
        self.open_cards.extend(cards)
        await TablesRelation.set_cards(self.table_id, self.remaining_deck, self.open_cards)

    async def reset_after_hand(self):
        await self.set_cards([], [])
        await self.clear_pots()
        await self.set_dealer(None)

    async def close(self):
        await gather(*[self.remove_player(player) for player in self.players.copy()])
        self.is_closed = True
        await TablesRelation.close_table(self.table_id)

    @classmethod
    async def ensure_free_tables(cls, number, table_config):
        tables = await Table.load_all()
        free_tables = len([table for table in tables if table.is_free()])
        if free_tables < number:
            await Table.create_tables(number - free_tables, table_config)
        return number - free_tables


class Pot:
    def __init__(self, bets=None):
        self.bets = bets or {}

    @property
    def amount(self):
        return sum(self.bets.values(), 0)

    @property
    def max_bet(self):
        return max(self.bets.values(), default=0)

    def bet(self, position):
        return self.bets.get(position, 0)

    def add_bet(self, position, bet):
        self.bets[position] = self.bet(position) + bet

    @property
    def positions(self):
        return set(self.bets.keys())

    def split(self, threshold):
        bets_in_new_pot = {position: bet - threshold for position, bet in self.bets.items() if bet > threshold}
        self.bets = {position: min(threshold, bet) for position, bet in self.bets.items()}
        return Pot(bets_in_new_pot)

    def to_dict(self):
        return {
            'bets': self.bets
        }
