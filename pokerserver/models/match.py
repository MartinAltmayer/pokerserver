import random

from asyncio import get_event_loop, sleep
from asyncio.tasks import gather
import logging
from uuid import uuid4

from pokerserver.configuration import ServerConfig
from pokerserver.database import DuplicateKeyError, PlayerState
from pokerserver.database import TableState
from .card import get_all_cards
from .player import Player
from .ranking import determine_winning_players
from .statistics import Statistics
from .table import Round

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
    def __init__(self, table, turn_delay=None, showdown_timeout=None):
        self.table = table
        self.turn_delay = turn_delay
        self.showdown_timeout = showdown_timeout

    async def check_and_unset_current_player(self, player_name):
        is_current_player = await self.table.check_and_unset_current_player(player_name)
        if not is_current_player:
            raise NotYourTurnError('It\'s not your turn')

    async def set_player_active(self, player):
        token = str(uuid4())

        if self.turn_delay is not None:
            await sleep(self.turn_delay)

        await self.table.set_current_player(player, token)

        timeout = ServerConfig.get('timeout')
        if timeout:
            get_event_loop().create_task(self.current_player_timeout(timeout, player, token))

    async def current_player_timeout(self, timeout, player, token):
        await sleep(timeout)
        await self.kick_if_current_player(player, token, 'timeout')

    async def kick_if_current_player(self, player, current_player_token, reason):
        is_current_player = await self.table.check_and_unset_current_player(player.name, current_player_token)
        if not is_current_player:
            return

        self.log(player, "Kicked due to: " + reason)
        next_player = self.find_next_player(player)
        if self.table.dealer.name == player.name:
            await self.table.set_dealer(self.table.player_right_of(self.table.dealer))

        await self.increment_stats_for_player(player)
        await self.table.remove_player(player)

        if len(self.table.players) > 1:
            if next_player is None:
                await self.next_round()
            else:
                await self.set_player_active(next_player)
        else:
            await self.close_table()

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
            await Player.sit_down(self.table, position, player_name, self.table.config.start_balance)
        except DuplicateKeyError:
            raise PositionOccupiedError()

        player = await Player.load_by_name(player_name)
        await self.table.add_player(player)

        self.log(player_name, 'Joined table {} at {}'.format(self.table.name, position))

        if self.table.is_waiting_for_players and len(self.table.players) == self.table.config.min_player_count:
            await self.start()

    async def start(self, dealer=None):
        await self.table.set_state(TableState.RUNNING_GAME)
        if dealer is None:
            dealer = random.choice(self.table.players)
        await self.table.reset()
        await self.start_hand(dealer)

    async def start_hand(self, dealer):
        assert len(self.table.players) >= 2
        await self.table.set_dealer(dealer)
        small_blind_player, big_blind_player = self.find_blind_players()
        under_the_gun = self.find_start_player()
        await self.pay_blinds(small_blind_player, big_blind_player)
        await self.distribute_cards()
        self.log(under_the_gun, "Started table {}".format(self.table.name))
        await self.set_player_active(under_the_gun)

    def find_blind_players(self):
        """Returns blind players independent of the progress of a match.

        Only players that are sitting out are ignored.
        """
        active_players = [player for player in self.table.players if player.state is not PlayerState.SITTING_OUT]
        if len(active_players) == 2:
            small_blind = self.table.dealer
            big_blind = self.table.player_left_of(small_blind, player_filter=active_players)
        else:
            small_blind = self.table.player_left_of(self.table.dealer, player_filter=active_players)
            big_blind = self.table.player_left_of(small_blind, player_filter=active_players)
        return small_blind, big_blind

    def find_start_player(self):
        """Find first player from small blind on that is playing (not sitting out)."""
        small_blind, big_blind = self.find_blind_players()
        if len(self.table.players) == 2:
            return small_blind if self.table.round == Round.PREFLOP else big_blind
        return self.table.player_left_of(big_blind) if self.table.round == Round.PREFLOP else small_blind

    def find_start_player_postflop(self):
        """Find first player from small blind on that is still playing (not folded, all in or sitting out)."""
        small_blind, big_blind = self.find_blind_players()
        active_players = [player for player in self.table.players if player.state is PlayerState.PLAYING]
        if len(active_players) == 2:
            start_player = small_blind if self.table.round == Round.PREFLOP else big_blind
        else:
            start_player = self.table.player_left_of(big_blind) if self.table.round == Round.PREFLOP else small_blind
        if start_player.state is not PlayerState.PLAYING:
            start_player = self.table.player_left_of(start_player, player_filter=active_players)
        return start_player

    async def pay_blinds(self, small_blind_player, big_blind_player):
        assert small_blind_player in self.table.players
        assert big_blind_player in self.table.players
        await self.make_player_pay(small_blind_player, self.table.config.small_blind)
        await self.make_player_pay(big_blind_player, self.table.config.big_blind)

    async def make_player_pay(self, player, amount):
        assert amount > 0, 'amount to pay must be greater than 0'
        paid_amount = amount if self.can_pay_amount(player, amount) else player.balance
        await player.increase_bet(paid_amount)
        await self.table.increase_pot(player.position, paid_amount)

    @staticmethod
    def can_pay_amount(player, amount):
        return player.balance >= amount

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
            await self.set_player_active(next_player)

    def find_next_player(self, current_player):
        active_players = [
            player for player in self.table.players
            if player.state not in [PlayerState.FOLDED, PlayerState.SITTING_OUT]
        ]

        if len(active_players) <= 1:
            return None

        active_players_not_all_in = [
            player for player in active_players
            if player.position == current_player.position or player.state is not PlayerState.ALL_IN
        ]

        if not active_players_not_all_in:
            return None

        if len(active_players_not_all_in) == 1 and active_players_not_all_in[0].position == current_player.position:
            return None

        next_player = self.table.player_left_of(current_player, active_players_not_all_in)
        if not self._may_make_another_turn(next_player, current_player):
            return None
        return next_player

    async def reset_bets(self):
        for player in self.table.players:
            await player.set_bet(0)

    async def next_round(self):
        await self.reset_bets()
        active_players = [player for player in self.table.players if player.state is PlayerState.PLAYING]
        all_in_players = [player for player in self.table.players if player.state is PlayerState.ALL_IN]

        if len(active_players) < 2:
            if all_in_players:
                if self.table.round is Round.PREFLOP:
                    await self.table.draw_cards(3)
                if self.table.round is Round.FLOP:
                    await self.table.draw_cards(1)
                if self.table.round is Round.TURN:
                    await self.table.draw_cards(1)
            await self.finish_hand()
            return

        if self.table.round is Round.PREFLOP:
            await self.table.draw_cards(3)
        elif self.table.round in [Round.FLOP, Round.TURN]:
            await self.table.draw_cards(1)
        else:
            await self.finish_hand()
            return

        next_player = self.find_start_player_postflop()
        self.log(next_player, 'Starts new round')
        await self.set_player_active(next_player)

    async def finish_hand(self):
        old_dealer = self.table.dealer
        await self.distribute_pots()
        if self.showdown_timeout:
            await sleep(self.showdown_timeout)
        await self.table.reset()

        dealer = self.table.player_left_of(old_dealer)
        while len(self.table.players) > 1:
            bankrupt_players = self.find_bankrupt_players()
            if not bankrupt_players:
                break

            for player in bankrupt_players:
                self.log(player, 'leaves the game')
                await self.increment_stats_for_player(player)
                await self.table.remove_player(player)
            if dealer in bankrupt_players:
                dealer = self.table.player_left_of(dealer)

        if len(self.table.players) > 1:
            await self.start_hand(dealer)
        else:
            await self.close_table()

    async def distribute_pots(self):
        active_players = self.table.active_players()

        for pot in self.table.pots:
            active_players_for_pot = [player for player in active_players if player.position in pot.bets.keys()]
            await self.distribute_pot(pot, active_players_for_pot)

    async def distribute_pot(self, pot, players):
        winning_players = determine_winning_players(players, self.table.open_cards) if len(players) > 1 else players

        for player in winning_players:
            await player.increase_balance(pot.amount // len(winning_players))

        rest = pot.amount % len(winning_players)
        if rest != 0:
            player = self.table.player_left_of(self.table.dealer, player_filter=players)
            await player.increase_balance(rest)

    def find_bankrupt_players(self):
        return [player for player in self.table.players if player.balance == 0]

    async def close_table(self):
        self.log('', 'Closing table {}'.format(self.table.table_id))
        await gather(*[self.increment_stats_for_player(player) for player in self.table.players])
        await self.table.close()

    async def increment_stats_for_player(self, player):
        await Statistics.increment_statistics(
            player.name, matches=1, buy_in=self.table.config.start_balance, gain=player.balance)

    async def call(self, player_name):
        player = self.table.find_player(player_name)
        highest_bet = self._get_highest_bet()
        if highest_bet <= player.bet:
            raise InvalidTurnError('Cannot call without higher bet, use \'check\' instead')

        await self.check_and_unset_current_player(player_name)
        await self.make_player_pay(player, highest_bet - player.bet)
        await self.next_player_or_round(player)

    async def check(self, player_name):
        player = self.table.find_player(player_name)
        if self._get_highest_bet() > player.bet:
            raise InvalidTurnError('Cannot check after a higher bet was made')
        await self.check_and_unset_current_player(player_name)
        await self.next_player_or_round(player)

    async def raise_bet(self, player_name, amount):
        player = self.table.find_player(player_name)
        highest_bet = self._get_highest_bet()
        if amount <= highest_bet - player.bet:
            raise InvalidBetError('Amount too low')
        if amount > player.balance:
            raise InsufficientBalanceError('Balance too low')
        await self.check_and_unset_current_player(player_name)
        await self.make_player_pay(player, amount)
        await self.next_player_or_round(player)

    def _get_highest_bet(self):
        return max([0] + [p.bet for p in self.table.players if p.bet is not None])

    def _may_make_another_turn(self, player, current_player):
        has_highest_bet = player.bet == self._get_highest_bet()
        if not has_highest_bet:
            return True
        elif player.bet > self._get_initial_bet(player):
            return False
        else:
            start_player = self.find_start_player()
            has_made_turn = player.position in self.table.player_positions_between(
                start_player.position, current_player.position)
            return not has_made_turn

    def _get_initial_bet(self, player):
        if self.table.round is not Round.PREFLOP:
            return 0

        small_blind_player, big_blind_player = self.find_blind_players()

        if player.position == small_blind_player.position:
            return self.table.config.small_blind
        elif player.position == big_blind_player.position:
            return self.table.config.big_blind
        else:
            return 0

    @staticmethod
    def log(player_or_name, message):
        LOG.info('[%s] %s', str(player_or_name), message)
