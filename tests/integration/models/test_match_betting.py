from unittest.mock import patch

from tornado.testing import gen_test

from pokerserver.database import PlayerState, PlayersRelation
from pokerserver.models import (InsufficientBalanceError, InvalidBetError, InvalidTurnError, Match, NotYourTurnError,
                                Player, Table)
from tests.utils import PotChecker, create_table, return_done_future


class BettingTestCase(PotChecker):
    async def async_setup(self, balances=(2, 2, 2, 2), bets=(0, 0, 0, 0)):
        assert len(balances) == len(bets)

        self.players = [
            Player(table_id=1, position=index + 1, name='John{}'.format(index), cards=[], balance=balance, bet=bet)
            for index, (balance, bet) in enumerate(zip(balances, bets))
        ]
        self.table = await create_table(players=self.players,
                                        pots=[{'bets': {(index + 1): bet for index, bet in enumerate(bets)}}])
        await self.table.set_dealer(self.players[0])
        if len(bets) == 2:
            await self.table.set_current_player(self.players[0], 'sometoken')
        else:
            await self.table.set_current_player(self.players[3 % len(self.players)], 'sometoken')
        self.match = Match(self.table)


class TestFold(BettingTestCase):
    @gen_test
    async def test_fold_invalid_player(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.fold(self.players[1].name)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_fold_sets_state_to_folded(self):
        await self.async_setup()

        await self.match.fold(self.players[3].name)

        player_data = await PlayersRelation.load_by_name(self.players[3].name)
        self.assertEqual(player_data['state'], PlayerState.FOLDED)

    @gen_test
    async def test_fold_changes_current_player(self):
        await self.async_setup()
        await self.match.fold(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)

    @gen_test
    async def test_fold_keeps_pots(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        await self.match.fold(self.players[3].name)
        await self.assert_pots(self.table.name)


class TestCall(BettingTestCase):
    @gen_test
    async def test_call_invalid_player(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[1].name)

        await self.assert_pots(self.table.name)

    @gen_test
    async def test_call_changes_current_player(self):
        await self.async_setup(bets=[0, 1, 2, 0])
        await self.assert_pots(self.table.name, amounts=[3])
        await self.match.call(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)

        await self.assert_pots(self.table.name, amounts=[5])

    @gen_test
    async def test_call_sufficient_balance(self):
        await self.async_setup(balances=[0, 1, 2, 12], bets=[0, 1, 5, 0])
        await self.assert_pots(self.table.name, amounts=[6])
        await self.match.call(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(5, player.bet)
        self.assertEqual(7, player.balance)
        self.assertEqual(PlayerState.PLAYING, player.state)

        await self.assert_pots(self.table.name, amounts=[11])

    @gen_test
    async def test_call_insufficient_balance(self):
        await self.async_setup(balances=[0, 1, 2, 10], bets=[3, 15, 0, 3])
        await self.assert_pots(self.table.name, amounts=[21])
        await self.match.call(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(13, player.bet)
        self.assertEqual(0, player.balance)
        self.assertEqual(PlayerState.ALL_IN, player.state)
        await self.assert_pots(self.table.name, amounts=[29, 2])

    @gen_test
    async def test_call_without_bet(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[0].name)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_call_without_higher_bet(self):
        await self.async_setup(balances=[10, 10, 10, 10], bets=[5, 5, 4, 4])
        await self.assert_pots(self.table.name, amounts=[18])
        with self.assertRaises(InvalidTurnError):
            await self.match.call(self.players[0].name)
        await self.assert_pots(self.table.name, amounts=[18])

    @gen_test
    async def test_call_heads_up(self):
        await self.async_setup(balances=[1, 0], bets=[1, 2])
        await self.assert_pots(self.table.name, amounts=[3])
        await self.match.call(self.players[0].name)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(2, player.bet)
        self.assertEqual(0, player.balance)
        await self.assert_pots(self.table.name, amounts=[4])

    @patch('pokerserver.models.match.Match.next_round', side_effect=return_done_future())
    @gen_test
    async def test_call_heads_up_big_blind(self, next_round_mock):
        await self.async_setup(balances=[1, 0], bets=[1, 2])
        await self.assert_pots(self.table.name, amounts=[3])
        await self.match.call(self.players[0].name)
        await self.match.check(self.players[1].name)

        player = await Player.load_by_name(self.players[1].name)
        self.assertEqual(2, player.bet)
        self.assertEqual(0, player.balance)
        await self.assert_pots(self.table.name, amounts=[4])
        next_round_mock.assert_called_once_with()

    @gen_test
    async def test_call_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.call(self.players[1].name)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_call_increases_pot(self):
        await self.async_setup(balances=[0, 1, 2, 12], bets=[0, 1, 5, 0])
        await self.assert_pots(self.table.name, amounts=[6])
        self.assertEqual(1, len(self.table.pots))
        self.assertEqual(6, self.table.pots[0].amount)
        await self.match.call(self.players[3].name)
        await self.assert_pots(self.table.name, amounts=[11])


class TestCheck(BettingTestCase):
    @gen_test
    async def test_check_invalid_player(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.check(self.players[2].name)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_check_changes_current_player(self):
        await self.async_setup(bets=[0, 0, 0, 0])
        await self.assert_pots(self.table.name)
        await self.match.check(self.players[3].name)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[0].name, table.current_player.name)

    @gen_test
    async def test_check_after_bet(self):
        await self.async_setup(bets=(1, 2, 1, 0))
        await self.assert_pots(self.table.name, amounts=[4])
        with self.assertRaises(InvalidTurnError):
            await self.match.check(self.players[3].name)
        await self.assert_pots(self.table.name, amounts=[4])

    @gen_test
    async def test_check(self):
        await self.async_setup(bets=[0, 0, 0, 0], balances=[2, 2, 2, 2])
        await self.assert_pots(self.table.name)
        await self.match.check(self.players[3].name)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(0, player.bet)
        self.assertEqual(2, player.balance)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_check_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        await self.assert_pots(self.table.name)
        await self.match.check(self.players[0].name)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(0, player.bet)
        self.assertEqual(2, player.balance)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_check_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.check(self.players[1].name)
        await self.assert_pots(self.table.name)


class TestRaise(BettingTestCase):
    @gen_test
    async def test_raise_invalid_player(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.raise_bet(self.players[1].name, 1)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_raise_amount_too_low(self):
        await self.async_setup(bets=[2, 5, 0, 0])
        await self.assert_pots(self.table.name, amounts=[7])
        with self.assertRaises(InvalidBetError):
            await self.match.raise_bet(self.players[3].name, 2)
        await self.assert_pots(self.table.name, amounts=[7])

    @gen_test
    async def test_raise_negative(self):
        await self.async_setup()
        await self.assert_pots(self.table.name)
        with self.assertRaises(InvalidBetError):
            await self.match.raise_bet(self.players[3].name, -1)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_raise_insufficient_balance(self):
        await self.async_setup(balances=[9, 0, 0, 0])
        await self.assert_pots(self.table.name)
        with self.assertRaises(InsufficientBalanceError):
            await self.match.raise_bet(self.players[3].name, 10)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_raise_changes_current_player(self):
        await self.async_setup(balances=[10, 0, 0], bets=[0, 0, 0])
        await self.match.raise_bet(self.players[0].name, 1)
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(self.players[1].name, table.current_player.name)

    @gen_test
    async def test_raise(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        await self.assert_pots(self.table.name)
        await self.match.raise_bet(self.players[3].name, 9)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(9, player.bet)
        self.assertEqual(1, player.balance)
        self.assertEqual(PlayerState.PLAYING, player.state)
        await self.assert_pots(self.table.name, amounts=[9])

    @gen_test
    async def test_raise_all_in(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        await self.assert_pots(self.table.name)
        await self.match.raise_bet(self.players[3].name, 10)
        player = await Player.load_by_name(self.players[3].name)
        self.assertEqual(10, player.bet)
        self.assertEqual(0, player.balance)
        self.assertEqual(PlayerState.ALL_IN, player.state)
        await self.assert_pots(self.table.name, amounts=[10])

    @gen_test
    async def test_raise_heads_up(self):
        await self.async_setup(balances=[10, 0], bets=[0, 0])
        await self.assert_pots(self.table.name)
        await self.match.raise_bet(self.players[0].name, 9)
        player = await Player.load_by_name(self.players[0].name)
        self.assertEqual(9, player.bet)
        self.assertEqual(1, player.balance)
        await self.assert_pots(self.table.name, amounts=[9])

    @gen_test
    async def test_raise_invalid_player_heads_up(self):
        await self.async_setup(balances=[2, 2], bets=[0, 0])
        await self.assert_pots(self.table.name)
        with self.assertRaises(NotYourTurnError):
            await self.match.raise_bet(self.players[1].name, 1)
        await self.assert_pots(self.table.name)

    @gen_test
    async def test_raise_increases_pot(self):
        await self.async_setup(balances=[0, 0, 0, 10])
        await self.assert_pots(self.table.name)
        await self.match.raise_bet(self.players[3].name, 8)
        await self.assert_pots(self.table.name, amounts=[8])

    @gen_test
    async def test_raise_creates_side_pot(self):
        await self.async_setup(balances=[20, 0, 0, 10])
        await self.assert_pots(self.table.name)
        await self.match.raise_bet(self.players[3].name, 10)
        await self.match.raise_bet(self.players[0].name, 20)
        await self.assert_pots(self.table.name, amounts=[20, 10])
