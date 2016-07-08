import random
import logging

from pokerserver.database.database import DuplicateKeyError
from pokerserver.models.card import get_all_cards
from pokerserver.models.player import Player

LOG = logging.getLogger(__name__)


class PositionOccupiedError(Exception):
    pass


class Match:
    def __init__(self, table):
        self.table = table

    def log(self, player_or_name, message):
        player_name = player_or_name if isinstance(player_or_name, str) else player_or_name.name
        LOG.info('[%s] %s', player_name, message)

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
            await Player.add_player(self.table, position, player_name, start_balance, '', 0)
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
        small_blind_player, big_blind_player, current_player = self.find_blind_players(self.table.dealer)
        await self.table.set_special_players(
            small_blind_player=small_blind_player, big_blind_player=big_blind_player, current_player=current_player)
        await self.pay_blinds()
        await self.distribute_cards()
        self.log(current_player, "Started table {}".format(self.table.name))

    def find_blind_players(self, dealer):
        if len(self.table.players) == 2:
            small_blind = dealer
            big_blind = self.table.player_left_of(small_blind)
            start_player = big_blind
        else:
            small_blind = self.table.player_left_of(dealer)
            big_blind = self.table.player_left_of(small_blind)
            start_player = self.table.player_left_of(big_blind)

        return small_blind, big_blind, start_player

    async def pay_blinds(self):
        # Players who cannot pay their blind should have been forced to leave the table.
        await self.table.small_blind_player.pay(self.table.config.small_blind)
        await self.table.big_blind_player.pay(self.table.config.big_blind)

    async def distribute_cards(self):
        cards = get_all_cards()
        random.shuffle(cards)
        for player in self.table.players:
            await player.set_cards([cards.pop(), cards.pop()])

        await self.table.set_cards(cards)
