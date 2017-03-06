from unittest.mock import ANY, call, patch

from tornado.testing import gen_test

from pokerserver.database import PlayerState, PlayersRelation, clear_relations
from pokerserver.models import Match, Player, Round, Table
from tests.utils import IntegrationTestCase, PotChecker, create_table, return_done_future


class TestNextRound(IntegrationTestCase, PotChecker):
    async def create_match(self, **kwargs):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 30),
            Player(table_id, 2, 'b', 10, [], 20),
            Player(table_id, 3, 'c', 10, [], 10),
            Player(table_id, 4, 'd', 10, [], 0),
            Player(table_id, 5, 'e', 10, [], 0, state=PlayerState.SITTING_OUT)
        ]

        table = await create_table(
            table_id=table_id, players=players, remaining_deck=['2c'] * 52, dealer=players[0].name,
            pots=[{'bets': {1: 10, 2: 10, 3: 10}}, {'bets': {1: 10, 2: 10}}, {'bets': {1: 10}}],
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
                await clear_relations()
                open_cards = ['2h'] * expected_card_count[round_of_match]
                match = await self.create_match(open_cards=open_cards)

                await match.next_round()

                self.assertEqual(rounds[i + 1], match.table.round)
                self.assertEqual(expected_card_count[match.table.round], len(match.table.open_cards))

    @gen_test
    async def test_reset_bets(self):
        match = await self.create_match()
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])
        await match.next_round()

        table = await Table.load_by_name(match.table.name)
        self.assertEqual({0}, {player.bet for player in table.players})
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])

    @gen_test
    async def test_player_state(self):
        match = await self.create_match()
        await match.next_round()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual(
            [PlayerState.PLAYING] * 4 + [PlayerState.SITTING_OUT],
            [player.state for player in table.players]
        )

    @gen_test
    async def test_switch_to_start_player(self):
        match = await self.create_match()
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])
        await match.table.set_current_player(match.table.players[1], 'sometoken')
        await match.next_round()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual(match.table.players[3].name, table.current_player.name)
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])

    @patch('pokerserver.models.match.Match.show_down', side_effect=return_done_future())
    @gen_test
    async def test_trigger_showdown(self, show_down_mock):
        match = await self.create_match(open_cards=['2h'] * 5)
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])
        await match.next_round()
        show_down_mock.assert_called_once_with()
        await self.assert_pots(match.table.name, amounts=[30, 20, 10])


class TestShowDown(IntegrationTestCase, PotChecker):
    start_balance = 30

    async def create_match(self, cards=None, **kwargs):
        cards = cards if cards is not None else [['Kc', '2c'], ['Ah', '2h'], ['Ks', '2s'], ['Kd', '2d']]
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, cards[0], 4),
            Player(table_id, 2, 'b', 10, cards[1], 2),
            Player(table_id, 3, 'c', 10, cards[2], 1),
            Player(table_id, 4, 'd', 10, cards[3], 0),
            Player(table_id, 5, 'e', 10, [], 0, state=PlayerState.SITTING_OUT)
        ]

        table = await create_table(
            table_id=table_id, players=players, start_balance=self.start_balance,
            dealer=players[0].name,
            pots=[{'bets': {1: 4, 2: 2, 3: 1}}],
            **kwargs
        )
        return Match(table)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pots_single_winner(self, start_hand_mock):
        match = await self.create_match()
        await self.assert_pots(match.table.name, amounts=[7])
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 17, 10, 10, 10], [player.balance for player in table.players])
        await self.assert_pots(match.table.name)
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pots_several_winners(self, start_hand_mock):
        match = await self.create_match(cards=[['Kc', '2c'], ['Ah', '2h'], ['As', '2s'], ['Ad', '2d']])
        await self.assert_pots(match.table.name, amounts=[7])
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 14, 13, 10, 10], [player.balance for player in table.players])
        await self.assert_pots(match.table.name)
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_reset(self, _):
        match = await self.create_match()
        await match.show_down()

        await self.assert_pots(match.table.name)
        table = await Table.load_by_name(match.table.name)
        for player in table.players:
            self.assertEqual(0, player.bet)
            self.assertEqual(PlayerState.PLAYING, player.state)

    @patch('pokerserver.models.match.Match.close_table', side_effect=return_done_future())
    @patch('pokerserver.models.match.Match.find_bankrupt_players')
    @gen_test
    async def test_close_table(self, bankrupt_players_mock, close_mock):
        match = await self.create_match()
        players = match.table.players.copy()
        bankrupt_players_mock.side_effect = [players[1:], []]

        await match.show_down()

        close_mock.assert_called_once_with()


class TestShowDownWithSidePots(IntegrationTestCase, PotChecker):
    start_balance = 30

    async def create_match(self, cards=None, **kwargs):
        cards = cards if cards is not None else [['Kc', '2c'], ['Ah', '2h'], ['Ks', '2s'], ['Kd', '2d']]
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, cards[0], 4, state=PlayerState.PLAYING),
            Player(table_id, 2, 'b', 0, cards[1], 2, state=PlayerState.ALL_IN),
            Player(table_id, 3, 'c', 0, cards[2], 1, state=PlayerState.ALL_IN),
            Player(table_id, 4, 'd', 10, cards[3], 0, state=PlayerState.FOLDED)
        ]

        table = await create_table(
            table_id=table_id, players=players, start_balance=self.start_balance,
            dealer=players[0].name,
            pots=[{'bets': {1: 1, 2: 1, 3: 1}}, {'bets': {1: 1, 2: 1}}, {'bets': {1: 2}}],
            **kwargs
        )
        return Match(table)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pots_single_winner(self, start_hand_mock):
        match = await self.create_match()
        await self.assert_pots(match.table.name, amounts=[3, 2, 2])
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([12, 5, 10], [player.balance for player in table.players])
        await self.assert_pots(match.table.name)
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pots_several_winners(self, start_hand_mock):
        match = await self.create_match(cards=[['Kc', '2c'], ['Ah', '2h'], ['As', '2s'], ['Ad', '2d']])
        await self.assert_pots(match.table.name, amounts=[3, 2, 2])
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([12, 4, 1, 10], [player.balance for player in table.players])
        await self.assert_pots(match.table.name)
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @patch('pokerserver.models.statistics.Statistics.increment_statistics', side_effect=return_done_future())
    @gen_test
    async def test_remove_bankrupt_players(self, increment_stats_mock, _):
        match = await self.create_match()
        await match.show_down()

        table = await Table.load_by_name(match.table.name)
        self.assertEqual(['a', 'b', 'd'], [player.name for player in table.players])

        self.assertIsNotNone(await PlayersRelation.load_by_position(match.table.table_id, 2))
        self.assertIsNone(await PlayersRelation.load_by_position(match.table.table_id, 3))

        increment_stats_mock.assert_has_calls([
            call('c', matches=1, buy_in=self.start_balance, gain=0),
        ], any_order=True)
