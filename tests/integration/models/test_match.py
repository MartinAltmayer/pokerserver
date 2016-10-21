# pylint: disable=no-self-use
from asyncio.tasks import gather
from unittest import TestCase
from unittest.mock import patch, Mock, call, ANY

from tornado.testing import gen_test

from pokerserver.database import Database, TableConfig
from pokerserver.database.players import PlayersRelation
from pokerserver.database.tables import TablesRelation
from pokerserver.models import (
    Player, get_all_cards, Match, Table, NotYourTurnError, PositionOccupiedError,
    InsufficientBalanceError, InvalidBetError, InvalidTurnError
)
from pokerserver.models.table import Round
from tests.integration.utils.integration_test import IntegrationTestCase, create_table, return_done_future


class TestJoin(IntegrationTestCase):
    async def async_setup(self, table_count=1, start_balance=10):
        self.player_name = 'player'
        config = TableConfig(min_player_count=2, max_player_count=2, small_blind=1, big_blind=2,
                             start_balance=start_balance)
        await Table.create_tables(table_count, config)
        await self.load_match()

    async def load_match(self):
        tables = await Table.load_all()
        self.table = tables[0]
        self.match = Match(self.table)

    async def check_players(self, expected_players):
        table = await Table.load_by_name(self.table.name)
        actual_players = {player.position: player.name for player in table.players}
        self.assertEqual(expected_players, actual_players)

    @gen_test
    async def test_join(self):
        await self.async_setup(start_balance=13)

        await self.match.join(self.player_name, 1)

        await self.check_players({1: self.player_name})
        self.assertEqual(self.player_name, self.table.players[0].name)
        self.assertEqual(1, self.table.players[0].position)
        self.assertEqual(13, self.table.players[0].balance)

    @gen_test
    async def test_joined_players(self):
        await self.async_setup(start_balance=10)
        await self.match.join(self.player_name, 1)

        table = await Table.load_by_name(self.table.name)
        self.assertEqual([self.player_name], table.joined_players)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET is_closed = 1 WHERE table_id = ?", self.table.table_id)
        await self.load_match()

        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 1)
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 3)
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(PositionOccupiedError):
            await self.match.join(self.player_name + '2', 1)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_at_table(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined_in_the_past(self):
        await self.async_setup()
        await TablesRelation.add_joined_player(self.table.table_id, self.player_name)
        await self.load_match()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2)

    @gen_test
    async def test_join_and_start(self):
        await self.async_setup()
        self.match.start = Mock(side_effect=return_done_future())
        await self.match.join(self.player_name, 1)
        self.match.start.assert_not_called()
        await self.match.join(self.player_name + ' II.', 2)
        self.match.start.assert_called_once_with()

    @gen_test
    async def test_join_two_tables(self):
        await self.async_setup(table_count=2)
        tables = await Table.load_all()
        self.assertEqual(len(tables), 2)
        for table in tables:
            match = Match(table)
            await match.join(self.player_name, 1)

    @gen_test
    async def test_join_concurrent(self):
        await self.async_setup()
        with self.assertRaises(PositionOccupiedError):
            await gather(
                self.match.join(self.player_name, 1),
                self.match.join('other player', 1),
                loop=self.get_asyncio_loop()
            )


class TestStartHand(IntegrationTestCase):
    @staticmethod
    def create_match(positions):
        table_id = 1
        players = [Player(table_id, position, name, 0, '', 0) for position, name in positions.items()]
        config = TableConfig(
            min_player_count=2, max_player_count=10, small_blind=1, big_blind=2, start_balance=10)
        return Match(Table(table_id, 'a table', config, players))

    def check_blind_players(self, players, small_blind, big_blind, start):
        self.assertEqual(players[0], small_blind.name)
        self.assertEqual(players[1], big_blind.name)
        self.assertEqual(players[2], start.name)

    def test_find_blind_players(self):
        match = self.create_match({1: 'a', 2: 'b', 3: 'c', 5: 'd'})
        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(1))
        self.check_blind_players('bcd', small_blind, big_blind, start)

        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(2))
        self.check_blind_players('cda', small_blind, big_blind, start)

    def test_find_blind_players_heads_up(self):
        match = self.create_match({1: 'a', 4: 'b'})
        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(1))
        self.check_blind_players('aba', small_blind, big_blind, start)

        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(4))
        self.check_blind_players('bab', small_blind, big_blind, start)

    def test_find_start_player(self):
        match = self.create_match({1: 'a', 2: 'b', 3: 'c', 5: 'd'})
        self.assertEqual('d', match.find_start_player(match.table.get_player_at(1), Round.preflop).name)
        self.assertEqual('d', match.find_start_player(match.table.get_player_at(1), Round.flop).name)

    def test_find_start_player_heads_up(self):
        match = self.create_match({1: 'a', 3: 'b'})
        self.assertEqual('a', match.find_start_player(match.table.get_player_at(1), Round.preflop).name)
        self.assertEqual('b', match.find_start_player(match.table.get_player_at(1), Round.flop).name)

    @patch('random.shuffle')
    @gen_test
    async def test_distribute_cards(self, shuffle_mock):
        table_id = 1
        cards = get_all_cards()
        shuffle_mock.return_value = reversed(cards)
        players = [
            Player(table_id, 1, 'a', 0, [], 0),
            Player(table_id, 2, 'b', 0, [], 0),
            Player(table_id, 5, 'c', 0, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players)
        match = Match(table)

        await match.distribute_cards()

        table = await Table.load_by_name(table.name)
        self.assertCountEqual(cards[-2:], table.players[0].cards)
        self.assertCountEqual(cards[-4:-2], table.players[1].cards)
        self.assertCountEqual(cards[-6:-4], table.players[2].cards)
        self.assertCountEqual(cards[:-6], table.remaining_deck)

    @patch('pokerserver.database.players.PlayersRelation.set_balance_and_bet', side_effect=return_done_future())
    @gen_test
    async def test_pay_blinds(self, set_balance_and_bet_mock):
        table_id = 1
        balance = 100
        players = [
            Player(table_id, 1, 'small_blind', balance, [], 0),
            Player(table_id, 2, 'big_blind', balance, [], 0),
            Player(table_id, 3, 'no_blind', balance, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players,
                                   small_blind_player='small_blind', big_blind_player='big_blind')
        match = Match(table)

        await match.pay_blinds()

        set_balance_and_bet_mock.assert_has_calls([
            call('small_blind', balance - table.config.small_blind, table.config.small_blind),
            call('big_blind', balance - table.config.big_blind, table.config.big_blind)
        ])

    @patch('random.choice')
    @gen_test
    async def test_start(self, choice_mock):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 10),
            Player(table_id, 2, 'b', 10, [], 20),
            Player(table_id, 3, 'c', 10, [], 30)
        ]

        table = await create_table(table_id=table_id, players=players)
        match = Match(table)
        choice_mock.return_value = table.get_player_at(2)

        await match.start()

        table = await Table.load_by_name(table.name)
        self.assertEqual(table.get_player_at(2), table.dealer)
        self.assertEqual(table.get_player_at(3), table.small_blind_player)
        self.assertEqual(table.get_player_at(1), table.big_blind_player)
        self.assertEqual(table.get_player_at(2), table.current_player)
        self.assertEqual(10, table.dealer.balance)
        self.assertEqual(9, table.small_blind_player.balance)
        self.assertEqual(8, table.big_blind_player.balance)
        self.assertEqual(0, table.dealer.bet)
        self.assertEqual(1, table.small_blind_player.bet)
        self.assertEqual(2, table.big_blind_player.bet)
        for player in table.players:
            self.assertEqual(2, len(player.cards))
        self.assertEqual(46, len(table.remaining_deck))
        self.assertEqual([], table.open_cards)


class BettingTestCase(IntegrationTestCase):
    async def async_setup(self, balances=(2, 2, 2, 2), bets=(0, 0, 0, 0)):
        assert len(balances) == len(bets)

        self.players = [
            Player(table_id=1, position=index + 1, name='John{}'.format(index), cards=[], balance=balance, bet=bet)
            for index, (balance, bet) in enumerate(zip(balances, bets))
        ]
        self.table = await create_table(players=self.players, main_pot=sum(bets))
        if len(bets) == 2:
            await self.table.set_special_players(
                dealer=self.players[0],
                small_blind_player=self.players[0],
                big_blind_player=self.players[1]
            )
            await self.table.set_current_player(self.players[0], 'sometoken')
        else:
            await self.table.set_special_players(
                dealer=self.players[0],
                small_blind_player=self.players[1 % len(self.players)],
                big_blind_player=self.players[2 % len(self.players)]
            )
            await self.table.set_current_player(self.players[3 % len(self.players)], 'sometoken')
        self.match = Match(self.table)


class TestFold(BettingTestCase):
    @gen_test
    async def test_fold_invalid_player(self):
        await self.async_setup()
        with self.assertRaises(NotYourTurnError):
            await self.match.fold(self.players[1].name)

    @gen_test
    async def test_fold_sets_has_folded(self):
        await self.async_setup()

        await self.match.fold(self.players[3].name)

        player_data = await PlayersRelation.load_by_name(self.players[3].name)
        self.assertTrue(player_data['has_folded'])

    @gen_test
    async def test_fold_changes_current_player(self):
        await self.async_setup()
        await self.match.fold(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)


class TestCall(BettingTestCase):
    @gen_test
    async def test_call_invalid_player(self):
        await self.async_setup()
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[1].name)

    @gen_test
    async def test_call_changes_current_player(self):
        await self.async_setup(bets=[0, 1, 2, 0])
        await self.match.call(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)

    @gen_test
    async def test_call_sufficient_balance(self):
        await self.async_setup(balances=[0, 1, 2, 12], bets=[0, 1, 5, 0])
        await self.match.call(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(5, player.bet)
        self.assertEqual(7, player.balance)

    @gen_test
    async def test_call_insufficient_balance(self):
        await self.async_setup(balances=[0, 1, 2, 10], bets=[3, 15, 0, 3])
        await self.match.call(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(13, player.bet)
        self.assertEqual(0, player.balance)

    @gen_test
    async def test_call_without_bet(self):
        await self.async_setup()
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[0].name)

    @gen_test
    async def test_call_heads_up(self):
        await self.async_setup(balances=[1, 0], bets=[1, 2])
        await self.match.call(self.players[0].name)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(2, player.bet)
        self.assertEqual(0, player.balance)

    @patch('pokerserver.models.match.Match.next_round', side_effect=return_done_future())
    @gen_test
    async def test_call_heads_up_big_blind(self, next_round_mock):
        await self.async_setup(balances=[1, 0], bets=[2, 2])
        await self.match.call(self.players[0].name)
        await self.match.call(self.players[1].name)

        player = await Player.load_by_name(self.players[1].name)
        self.assertEqual(2, player.bet)
        self.assertEqual(0, player.balance)
        next_round_mock.assert_called_once_with()

    @gen_test
    async def test_call_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[1].name)

    @gen_test
    async def test_call_increases_pot(self):
        await self.async_setup(balances=[0, 1, 2, 12], bets=[0, 1, 5, 0])
        self.assertEqual(6, self.table.main_pot)

        await self.match.call(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(11, table.main_pot)


class TestCheck(BettingTestCase):
    @gen_test
    async def test_check_invalid_player(self):
        await self.async_setup()
        with self.assertRaises(NotYourTurnError):
            await self.match.check(self.players[2].name)

    @gen_test
    async def test_check_changes_current_player(self):
        await self.async_setup(bets=[0, 0, 0, 0])
        await self.match.check(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)

    @gen_test
    async def test_check_after_bet(self):
        await self.async_setup(bets=(1, 2, 1, 0))
        with self.assertRaises(InvalidTurnError):
            await self.match.check(self.players[3].name)

    @gen_test
    async def test_check(self):
        await self.async_setup(bets=[0, 0, 0, 0], balances=[2, 2, 2, 2])
        await self.match.check(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(0, player.bet)
        self.assertEqual(2, player.balance)

    @gen_test
    async def test_check_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        await self.match.check(self.players[0].name)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(0, player.bet)
        self.assertEqual(2, player.balance)

    @gen_test
    async def test_check_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.check(self.players[1].name)


class TestRaise(BettingTestCase):
    @gen_test
    async def test_raise_invalid_player(self):
        await self.async_setup()
        with self.assertRaises(NotYourTurnError):
            await self.match.raise_bet(self.players[1].name, 1)

    @gen_test
    async def test_raise_amount_too_low(self):
        await self.async_setup(bets=[2, 5, 0, 0])
        with self.assertRaises(InvalidBetError):
            await self.match.raise_bet(self.players[3].name, 2)

    @gen_test
    async def test_raise_negative(self):
        await self.async_setup()
        with self.assertRaises(InvalidBetError):
            await self.match.raise_bet(self.players[3].name, -1)

    @gen_test
    async def test_raise_insufficient_balance(self):
        await self.async_setup(balances=[9, 0, 0, 0])
        with self.assertRaises(InsufficientBalanceError):
            await self.match.raise_bet(self.players[3].name, 10)

    @gen_test
    async def test_raise_changes_current_player(self):
        await self.async_setup(balances=[10, 0, 0], bets=[0, 0, 0])
        await self.match.raise_bet(self.players[0].name, 1)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[1].name, table.current_player.name)

    @gen_test
    async def test_raise(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        await self.match.raise_bet(self.players[3].name, 9)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(9, player.bet)
        self.assertEqual(1, player.balance)

    @gen_test
    async def test_raise_heads_up(self):
        await self.async_setup(balances=[10, 0], bets=[0, 0])
        await self.match.raise_bet(self.players[0].name, 9)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(9, player.bet)
        self.assertEqual(1, player.balance)

    @gen_test
    async def test_raise_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.raise_bet(self.players[1].name, 1)

    @gen_test
    async def test_raise_sets_highest_bet_player(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        self.assertIsNone(self.table.highest_bet_player)

        await self.match.raise_bet(self.players[3].name, 9)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[3].name, table.highest_bet_player.name)

    @gen_test
    async def test_raise_increases_pot(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        self.assertEqual(0, self.table.main_pot)

        await self.match.raise_bet(self.players[3].name, 10)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(10, table.main_pot)


class TestFindNextPlayer(TestCase):
    def setUp(self):
        super().setUp()
        config = TableConfig(
            min_player_count=2, max_player_count=4, big_blind=2, small_blind=1, start_balance=10)
        self.table = Table(1, 'test', config)
        self.table.players = self.create_players(6)
        self.sorted_players = sorted(self.table.players, key=lambda p: p.position)
        self.table.dealer = self.table.players[0]
        self.match = Match(self.table)

    def create_players(self, count):
        # make sure that the positional order differs from the order in the list
        players = [Mock(spec=Player, position=count - position, has_folded=False) for position in range(count)]
        for player in players:
            player.name = 'p{}'.format(player.position)
        return players

    def test_find_next_player_basic(self):
        players = self.sorted_players
        self.assertEqual(players[3], self.match.find_next_player(players[2]))
        self.assertEqual(players[0], self.match.find_next_player(players[5]))

    def test_find_next_player_inactive(self):
        players = self.sorted_players
        players[3].has_folded = True
        self.assertEqual(players[4], self.match.find_next_player(players[2]))

    def test_find_next_player_all_inactive(self):
        players = self.sorted_players
        for player in players:
            player.has_folded = True
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_all_inactive_except_current(self):
        players = self.sorted_players
        for player in players[1:]:
            player.has_folded = True
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_has_highest_bet(self):
        players = self.sorted_players
        self.assertEqual(players[1], self.match.find_next_player(players[0]))

        self.table.highest_bet_player = players[1]
        self.assertIsNone(self.match.find_next_player(players[0]))

    def test_find_next_player_has_already_played(self):
        players = self.sorted_players

        next_player = self.match.find_next_player(players[2])
        self.assertEqual(players[3], next_player)
        next_player = self.match.find_next_player(players[1])
        self.assertIsNone(next_player)

    def test_find_next_player_heads_up(self):
        self.table.players = players = self.create_players(2)
        self.table.dealer = players[0]

        self.assertEqual(players[1], self.match.find_next_player(players[0]))
        self.assertIsNone(self.match.find_next_player(players[1]))

        self.table.highest_bet_player = players[0]
        self.assertEqual(players[1], self.match.find_next_player(players[0]))


class TestNextRound(IntegrationTestCase):
    async def create_match(self, **kwargs):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 30),
            Player(table_id, 2, 'b', 10, [], 20),
            Player(table_id, 3, 'c', 10, [], 10),
            Player(table_id, 4, 'd', 10, [], 0)
        ]

        table = await create_table(
            table_id=table_id, players=players, remaining_deck=['2c'] * 52,
            dealer=players[0].name, small_blind_player=players[1].name, big_blind_player=players[2].name,
            highest_bet_player=players[0].name,
            **kwargs
        )
        return Match(table)

    @gen_test
    async def test_draw_open_cards(self):
        expected_card_count = {
            Round.preflop: 0,
            Round.flop: 3,
            Round.turn: 4,
            Round.river: 5
        }
        rounds = list(Round)
        for i, round_of_match in enumerate(rounds[:-1]):
            with self.subTest(round=round_of_match):
                await Database.instance().clear_tables()
                open_cards = ['2h'] * expected_card_count[round_of_match]
                match = await self.create_match(open_cards=open_cards)

                await match.next_round()

                self.assertEqual(rounds[i + 1], match.table.round)
                self.assertEqual(expected_card_count[match.table.round], len(match.table.open_cards))

    @gen_test
    async def test_reset_bets(self):
        match = await self.create_match()
        await match.next_round()

        table = await Table.load_by_name(match.table.name)
        for player in table.players:
            self.assertEqual(0, player.bet)

    @gen_test
    async def test_reset_highest_bet_player(self):
        match = await self.create_match()
        await match.next_round()
        table = await Table.load_by_name(match.table.name)
        self.assertIsNone(table.highest_bet_player)

    @gen_test
    async def test_switch_to_start_player(self):
        match = await self.create_match()
        await match.table.set_current_player(match.table.players[1], 'sometoken')
        await match.next_round()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual(match.table.players[3].name, table.current_player.name)

    @patch('pokerserver.models.match.Match.show_down', side_effect=return_done_future())
    @gen_test
    async def test_trigger_showdown(self, show_down_mock):
        match = await self.create_match(open_cards=['2h'] * 5)
        await match.next_round()
        show_down_mock.assert_called_once_with()


class TestShowDown(IntegrationTestCase):
    start_balance = 30

    async def create_match(self, **kwargs):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, ['Ac', '2c'], 4),
            Player(table_id, 2, 'b', 10, ['Ah', '2h'], 2),
            Player(table_id, 3, 'c', 10, ['As', '2s'], 1),
            Player(table_id, 4, 'd', 10, ['Ad', '2d'], 0)
        ]

        table = await create_table(
            table_id=table_id, players=players, start_balance=self.start_balance,
            dealer=players[0].name, small_blind_player=players[1].name, big_blind_player=players[2].name,
            **kwargs
        )
        return Match(table)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pot_single_winner(self, start_hand_mock, winning_players_mock):
        match = await self.create_match(main_pot=7)
        winning_players_mock.return_value = [match.table.players[1]]
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 17, 10, 10], [player.balance for player in table.players])
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pot_several_winners(self, start_hand_mock, winning_players_mock):
        match = await self.create_match(main_pot=7)
        winning_players_mock.return_value = match.table.players[1:]
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 13, 12, 12], [player.balance for player in table.players])
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_reset(self, _, winning_players_mock):
        match = await self.create_match(main_pot=2)
        winning_players_mock.return_value = [match.table.players[1]]
        await match.show_down()

        table = await Table.load_by_name(match.table.name)
        self.assertEqual(0, table.main_pot)
        for player in table.players:
            self.assertEqual(0, player.bet)
            self.assertFalse(player.has_folded)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @patch('pokerserver.models.match.Match.find_bankrupt_players')
    @patch('pokerserver.database.stats.StatsRelation.increment_stats', side_effect=return_done_future())
    @gen_test
    async def test_remove_bankrupt_players(self, increment_stats_mock, bankrupt_players_mock, _,
                                           winning_players_mock):
        match = await self.create_match()
        players = match.table.players.copy()
        winning_players_mock.return_value = [players[0]]
        bankrupt_players_mock.side_effect = [[players[1]], [players[2]], []]
        players[1].balance = players[2].balance = 0

        await match.show_down()

        self.assertEqual(3, bankrupt_players_mock.call_count)
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([players[0].name, players[3].name], [player.name for player in table.players])

        self.assertIsNone(await PlayersRelation.load_by_position(match.table.table_id, players[1].position))
        self.assertIsNone(await PlayersRelation.load_by_position(match.table.table_id, players[2].position))

        increment_stats_mock.assert_has_calls([
            call(players[1].name, matches=1, buy_in=self.start_balance, gain=0),
            call(players[2].name, matches=1, buy_in=self.start_balance, gain=0),
        ], any_order=True)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.close_table', side_effect=return_done_future())
    @patch('pokerserver.models.match.Match.find_bankrupt_players')
    @gen_test
    async def test_close_table(self, bankrupt_players_mock, close_mock, winning_players_mock):
        match = await self.create_match()
        players = match.table.players.copy()
        winning_players_mock.return_value = [players[0]]
        bankrupt_players_mock.side_effect = [players[1:], []]

        await match.show_down()

        close_mock.assert_called_once_with()


class TestFindBankruptPlayers(IntegrationTestCase):
    async def create_match(self, *balances):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', balances[0], [], 0),
            Player(table_id, 2, 'b', balances[1], [], 0),
            Player(table_id, 3, 'c', balances[2], [], 0),
            Player(table_id, 4, 'd', balances[3], [], 0)
        ]

        table = await create_table(table_id=table_id, players=players, small_blind=10, big_blind=20)
        return Match(table)

    @gen_test
    async def test_bankrupt_players(self):
        match = await self.create_match(0, 20, 20, 0)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[0], players[3]], bankrupt_players)

    @gen_test
    async def test_small_blind_bankrupt(self):
        match = await self.create_match(20, 9, 20, 20)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[1]], bankrupt_players)

    @gen_test
    async def test_big_blind_bankrupt(self):
        match = await self.create_match(20, 10, 19, 20)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[2]], bankrupt_players)

    @gen_test
    async def test_noone_bankrupt(self):
        match = await self.create_match(1, 10, 20, 1)
        self.assertEqual([], match.find_bankrupt_players(dealer=match.table.players[0]))
