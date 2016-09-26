import logging
import random

from asyncio.tasks import gather

from pokerserver.database import DuplicateKeyError
from pokerserver.database.stats import StatsRelation
from pokerserver.models.table import Round
from .card import get_all_cards
from .player import Player
from .ranking import determine_winning_players

LOG = logging.getLogger(__name__)


class PositionOccupiedError(Exception):
    pass


class InvalidTurnError(Exception):
    pass


class NotYourTurnError(InvalidTurnError):
    pass


class InsufficientBalanceError(InvalidTurnError):
    pass


class InvalidBetError(InvalidTurnError):
    pass


class Match:  # pylint: disable=too-many-public-methods
    def __init__(self, table):
        self.table = table

    async def check_and_unset_current_player(self, player_name):
        is_current_player = await self.table.check_and_unset_current_player(player_name)
        if not is_current_player:
            raise NotYourTurnError('It\'s not your turn')

    async def join(self, player_name, position):
        if self.table.is_closed:
            raise ValueError('Table is closed')
        if not self.table.is_position_valid(position):
            raise ValueError('Invalid position')
        if not self.table.is_position_free(position):
            raise PositionOccupiedError()
        if self.table.is_player_at_table(player_name) or player_name in self.table.joined_players:
            raise ValueError('Player has already joined')

        try:
            await Player.add_player(self.table, position, player_name, self.table.config.start_balance)
        except DuplicateKeyError:
            raise PositionOccupiedError()

        player = await Player.load_by_name(player_name)
        await self.table.add_player(player)

        self.log(player_name, 'Joined table {} at {}'.format(self.table.name, position))

        if len(self.table.players) == self.table.config.min_player_count:
            await self.start()

    async def start(self, dealer=None):
        await self.table.set_special_players(dealer=dealer or random.choice(self.table.players))
        await self.start_hand()

    async def start_hand(self):
        assert len(self.table.players) >= 2
        small_blind_player, big_blind_player, under_the_gun = self.find_blind_players(self.table.dealer)
        await self.table.set_special_players(
            small_blind_player=small_blind_player,
            big_blind_player=big_blind_player,
            current_player=under_the_gun,
            highest_bet_player=None
        )
        await self.reset_bets()
        await self.pay_blinds()
        await self.distribute_cards()
        self.log(under_the_gun, "Started table {}".format(self.table.name))

    def find_blind_players(self, dealer):
        if len(self.table.players) == 2:
            small_blind = dealer
            big_blind = self.table.player_left_of(small_blind)
            under_the_gun = small_blind
        else:
            small_blind = self.table.player_left_of(dealer)
            big_blind = self.table.player_left_of(small_blind)
            under_the_gun = self.table.player_left_of(big_blind)

        return small_blind, big_blind, under_the_gun

    def find_start_player(self, dealer, round_of_match):
        _, big_blind, start_player = self.find_blind_players(dealer)
        if round_of_match is not Round.preflop and len(self.table.players) == 2:
            start_player = big_blind
        return start_player

    async def pay_blinds(self):
        # If a player cannot pay a blind, the pot should be split up.
        await self.table.small_blind_player.increase_bet(self.table.config.small_blind)
        await self.table.big_blind_player.increase_bet(self.table.config.big_blind)
        await self.table.set_pot(self.table.config.small_blind + self.table.config.big_blind)

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
        next_player = self.find_next_player(current_player)
        if next_player is None:
            await self.next_round()
        else:
            await self.table.set_current_player(next_player)

    def find_next_player(self, current_player):
        active_players = [player for player in self.table.players if not player.has_folded]
        if len(active_players) <= 1:
            return None

        next_player = self.table.player_left_of(current_player, active_players)
        if next_player == self.table.highest_bet_player:
            return None

        if self.table.highest_bet_player is None and self._has_made_turn(next_player, current_player):
            return None
        return next_player

    async def reset_bets(self):
        await Player.reset_bets(self.table.table_id)
        for player in self.table.players:
            player.bet = 0

    async def next_round(self):
        await self.reset_bets()
        if self.table.round is Round.preflop:
            await self.table.draw_cards(3)
        elif self.table.round in [Round.flop, Round.turn]:
            await self.table.draw_cards(1)
        else:
            await self.show_down()
            return

        next_player = self.find_start_player(self.table.dealer, self.table.round)
        await self.table.set_special_players(
            current_player=next_player,
            highest_bet_player=None
        )
        self.log(next_player, 'Starts new round')

    async def show_down(self):
        await self.distribute_pot()
        await Player.reset_after_hand(self.table.table_id)
        old_dealer = self.table.dealer
        await self.table.reset_after_hand()

        dealer = self.table.player_left_of(old_dealer)
        bankrupt_players = self.find_bankrupt_players(dealer)
        while len(bankrupt_players) > 0 and len(self.table.players) > 1:
            for player in bankrupt_players:
                self.log(player, 'leaves the game')
                await self.increment_stats_for_player(player)
                await self.table.remove_player(player)
            if dealer in bankrupt_players:
                dealer = self.table.player_left_of(dealer)
            bankrupt_players = self.find_bankrupt_players(dealer)

        if len(self.table.players) > 1:
            await self.start_hand()
        else:
            await self.close_table()

    async def distribute_pot(self):
        active_players = self.table.active_players()
        winning_players = determine_winning_players(active_players, self.table.open_cards)
        for player in winning_players:
            await player.increase_balance(self.table.main_pot // len(winning_players))
        rest = self.table.main_pot % len(winning_players)
        if rest != 0:
            player = self.table.player_left_of(self.table.dealer, player_filter=active_players)
            await player.increase_balance(rest)

    def find_bankrupt_players(self, dealer):
        small_blind_player, big_blind_player, _ = self.find_blind_players(dealer)
        bankrupt_players = []
        for player in self.table.players:
            if player == small_blind_player:
                required_balance = self.table.config.small_blind
            elif player == big_blind_player:
                required_balance = self.table.config.big_blind
            else:
                required_balance = 1

            if player.balance < required_balance:
                bankrupt_players.append(player)

        return bankrupt_players

    async def close_table(self):
        await gather(*[self.increment_stats_for_player(player) for player in self.table.players])
        await self.table.close()

    async def increment_stats_for_player(self, player):
        await StatsRelation.increment_stats(
            player.name, matches=1, buy_in=self.table.config.start_balance, gain=player.balance)

    async def call(self, player_name):
        await self.check_and_unset_current_player(player_name)
        player = self.table.find_player(player_name)
        highest_bet = self._get_highest_bet()
        if highest_bet == 0:
            raise InvalidTurnError('Cannot call without bet, use \'check\' instead')
        increase = min(player.balance, highest_bet - player.bet)
        if increase > 0:
            await player.increase_bet(increase)
            await self.table.increase_pot(increase)
        else:
            # This happens if both the small blind and the big blind call at the beginning of a hand.
            assert len(self.table.players) == 2
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
            raise InvalidBetError('Amount too low')
        if amount > player.balance:
            raise InsufficientBalanceError('Balance too low')
        await player.increase_bet(amount)
        await self.table.increase_pot(amount)
        await self.table.set_special_players(highest_bet_player=player)
        await self.next_player_or_round(player)

    def _get_highest_bet(self):
        return max([0] + [p.bet for p in self.table.players if p.bet is not None])

    def _has_made_turn(self, player, current_player):
        start_player = self.find_start_player(self.table.dealer, self.table.round)
        return player.position in self.table.player_positions_between(
            start_player.position, current_player.position)

    @staticmethod
    def log(player_or_name, message):
        player_name = player_or_name if isinstance(player_or_name, str) else player_or_name.name
        LOG.info('[%s] %s', player_name, message)
