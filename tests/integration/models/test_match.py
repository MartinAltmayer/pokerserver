# pylint: disable=no-self-use
from asyncio.tasks import gather
from unittest import TestCase
from unittest.mock import patch, Mock, call

from tornado.testing import gen_test

from pokerserver.database import Database, TableConfig
from pokerserver.database.players import PlayersRelation
from pokerserver.models import (
    Player, get_all_cards, Match, Table, NotYourTurnError, PositionOccupiedError,
    InsufficientBalanceError, InvalidBetError, InvalidTurnError
)
from tests.integration.utils.integration_test import IntegrationTestCase, create_table, return_done_future


class TestJoin(IntegrationTestCase):
    async def async_setup(self, table_count=1):
        self.player_name = 'player'
        config = TableConfig(min_player_count=2, max_player_count=2, small_blind=1, big_blind=2)
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
        start_balance = 13
        await self.async_setup()

        await self.match.join(self.player_name, 1, start_balance)

        await self.check_players({1: self.player_name})
        self.assertEqual(self.player_name, self.table.players[0].name)
        self.assertEqual(1, self.table.players[0].position)
        self.assertEqual(start_balance, self.table.players[0].balance)

    @gen_test
    async def test_join_closed(self):
        await self.async_setup()
        await Database.instance().execute("UPDATE tables SET is_closed = 1 WHERE table_id = ?", self.table.table_id)
        await self.load_match()

        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 1, 0)
        await self.check_players({})

    @gen_test
    async def test_join_invalid_position(self):
        await self.async_setup()
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 0, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 3, 0)
        await self.check_players({})

    @gen_test
    async def test_join_occupied_position(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1, 0)
        with self.assertRaises(PositionOccupiedError):
            await self.match.join(self.player_name + '2', 1, 0)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_already_joined(self):
        await self.async_setup()
        await self.match.join(self.player_name, 1, 0)
        with self.assertRaises(ValueError):
            await self.match.join(self.player_name, 2, 0)
        await self.check_players({1: self.player_name})

    @gen_test
    async def test_join_and_start(self):
        await self.async_setup()
        self.match.start = Mock(side_effect=return_done_future())
        await self.match.join(self.player_name, 1, 0)
        self.match.start.assert_not_called()
        await self.match.join(self.player_name + ' II.', 2, 0)
        self.match.start.assert_called_once_with()

    @gen_test
    async def test_join_two_tables(self):
        await self.async_setup(table_count=2)
        tables = await Table.load_all()
        self.assertEqual(len(tables), 2)
        for table in tables:
            match = Match(table)
            await match.join(self.player_name, 1, 0)

    @gen_test
    async def test_join_concurrent(self):
        await self.async_setup()
        with self.assertRaises(PositionOccupiedError):
            await gather(
                self.match.join(self.player_name, 1, 0),
                self.match.join('other player', 1, 0),
                loop=self.get_asyncio_loop()
            )


class TestStartRound(IntegrationTestCase):
    @staticmethod
    def create_match(positions):
        table_id = 1
        players = [Player(table_id, position, name, 0, '', 0) for position, name in positions.items()]
        config = TableConfig(min_player_count=2, max_player_count=10, small_blind=1, big_blind=2)
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
        self.check_blind_players('abb', small_blind, big_blind, start)

        small_blind, big_blind, start = match.find_blind_players(match.table.get_player_at(4))
        self.check_blind_players('baa', small_blind, big_blind, start)

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
            Player(table_id, 1, 'a', 10, [], 0),
            Player(table_id, 2, 'b', 10, [], 0),
            Player(table_id, 3, 'c', 10, [], 0)
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
        self.table = await create_table(players=self.players)
        await self.table.set_special_players(
            dealer=self.players[0],
            small_blind_player=self.players[1 % len(self.players)],
            big_blind_player=self.players[2 % len(self.players)],
            current_player=self.players[3 % len(self.players)])
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
        await self.async_setup(balances=[2, 2], bets=[2, 0])
        await self.match.call(self.players[1].name)
        player = await Player.load_by_name(self.players[1].name)
        self.assertEqual(2, player.bet)
        self.assertEqual(0, player.balance)

    @gen_test
    async def test_call_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[0].name)


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
        await self.match.check(self.players[1].name)
        player = await Player.load_by_name(self.players[1].name)
        self.assertEqual(0, player.bet)
        self.assertEqual(2, player.balance)

    @gen_test
    async def test_check_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.check(self.players[0].name)


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
        await self.async_setup(balances=[0, 10], bets=[0, 0])
        await self.match.raise_bet(self.players[1].name, 9)
        player = await Player.load_by_name(self.players[1].name)
        self.assertEqual(9, player.bet)
        self.assertEqual(1, player.balance)

    @gen_test
    async def test_raise_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        with self.assertRaises(NotYourTurnError):
            await self.match.raise_bet(self.players[0].name, 1)


class TestFindNextPlayer(TestCase):
    def setUp(self):
        super().setUp()
        config = TableConfig(min_player_count=2, max_player_count=4, big_blind=2, small_blind=1)
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

        self.assertEqual(players[0], self.match.find_next_player(players[1]))
        self.assertIsNone(self.match.find_next_player(players[0]))

        self.table.highest_bet_player = players[0]
        self.assertEqual(players[1], self.match.find_next_player(players[0]))
