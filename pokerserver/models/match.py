import logging
import random

from pokerserver.database import DuplicateKeyError
from .card import get_all_cards
from .player import Player

LOG = logging.getLogger(__name__)


class PositionOccupiedError(Exception):
    pass


class InvalidTurnError(Exception):
    pass


class Match:
    def __init__(self, table):
        self.table = table

    async def check_and_unset_current_player(self, player_name):
        is_current_player = await self.table.check_and_unset_current_player(player_name)
        if not is_current_player:
            raise InvalidTurnError('It\'s not your turn')

    async def join(self, player_name, position, start_balance):
        if self.table.is_closed:
            raise ValueError('Table is closed')
        if not self.table.is_position_valid(position):
            raise ValueError('Invalid position')
        if not self.table.is_position_free(position):
            raise PositionOccupiedError()
        if self.table.is_player_at_table(player_name):
            raise ValueError('Player has already joined')

        try:
            await Player.add_player(self.table, position, player_name, start_balance)
        except DuplicateKeyError:
            raise PositionOccupiedError()

        player = await Player.load_by_name(player_name)
        self.table.players.append(player)

        self.log(player_name, 'Joined table {} at {}'.format(self.table.name, position))

        if len(self.table.players) == self.table.config.min_player_count:
            await self.start()

    async def start(self):
        await self.table.set_special_players(dealer=random.choice(self.table.players))
        await self.start_hand()

    async def start_hand(self):
        assert len(self.table.players) >= 2
        small_blind_player, big_blind_player, under_the_gun = self.find_blind_players(self.table.dealer)
        await self.table.set_special_players(
            small_blind_player=small_blind_player, big_blind_player=big_blind_player, current_player=under_the_gun)
        await self.pay_blinds()
        await self.distribute_cards()
        self.log(under_the_gun, "Started table {}".format(self.table.name))

    def find_blind_players(self, dealer):
        if len(self.table.players) == 2:
            small_blind = dealer
            big_blind = self.table.player_left_of(small_blind)
            under_the_gun = big_blind
        else:
            small_blind = self.table.player_left_of(dealer)
            big_blind = self.table.player_left_of(small_blind)
            under_the_gun = self.table.player_left_of(big_blind)

        return small_blind, big_blind, under_the_gun

    async def pay_blinds(self):
        # Players who cannot pay their blind should have been forced to leave the table.
        await self.table.small_blind_player.increase_bet(self.table.config.small_blind)
        await self.table.big_blind_player.increase_bet(self.table.config.big_blind)

    async def distribute_cards(self):
        cards = get_all_cards()
        random.shuffle(cards)
        for player in self.table.players:
            await player.set_cards([cards.pop(), cards.pop()])

        await self.table.set_cards(cards)

    async def fold(self, player_name):
        await self.check_and_unset_current_player(player_name)
        player = self.table.find_player(player_name)
        await player.fold()
        await self.next_player_or_round(player)

    async def next_player_or_round(self, current_player):
        # This has to be extended.
        await self.table.set_current_player(self.table.player_left_of(current_player))

    async def call(self, player_name):
        await self.check_and_unset_current_player(player_name)
        player = self.table.find_player(player_name)
        highest_bet = self._get_highest_bet()
        if highest_bet == 0:
            raise InvalidTurnError('Cannot call without bet, use \'check\' instead')
        increase = min(player.balance, highest_bet - player.bet)
        await player.increase_bet(increase)
        await self.next_player_or_round(player)

    async def check(self, player_name):
        await self.check_and_unset_current_player(player_name)
        player = self.table.find_player(player_name)
        if self._get_highest_bet() > 0:
            raise InvalidTurnError('Cannot check after a bet was made')
        await self.next_player_or_round(player)

    async def raise_bet(self, player_name, amount):
        await self.check_and_unset_current_player(player_name)
        player = self.table.find_player(player_name)
        highest_bet = self._get_highest_bet()
        if amount <= highest_bet - player.bet:
            raise InvalidTurnError('Amount too low')
        if amount > player.balance:
            raise InvalidTurnError('Balance too low')
        await player.increase_bet(amount)
        await self.next_player_or_round(player)

    def _get_highest_bet(self):
        return max(p.bet for p in self.table.players)

    @staticmethod
    def log(player_or_name, message):
        player_name = player_or_name if isinstance(player_or_name, str) else player_or_name.name
        LOG.info('[%s] %s', player_name, message)
