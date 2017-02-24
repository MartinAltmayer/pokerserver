from unittest.mock import ANY, call, patch

from tornado.testing import gen_test

from pokerserver.database import PlayerState, PlayersRelation, clear_relations
from pokerserver.models import Match, Player, Round, Table
from tests.utils import IntegrationTestCase, PotChecker, create_table, return_done_future


class TestNextRound(PotChecker):
    async def create_match(self, **kwargs):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', 10, [], 30),
            Player(table_id, 2, 'b', 10, [], 20),
            Player(table_id, 3, 'c', 10, [], 10),
            Player(table_id, 4, 'd', 10, [], 0)
        ]

        table = await create_table(
            table_id=table_id, players=players, remaining_deck=['2c'] * 52, dealer=players[0].name,
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
        await match.next_round()

        table = await Table.load_by_name(match.table.name)
        for player in table.players:
            self.assertEqual(0, player.bet)

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
    # Extend to side pots

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
            dealer=players[0].name,
            pots=[{'bets': {1: 4, 2: 2, 3: 1}}],
            **kwargs
        )
        return Match(table)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pot_single_winner(self, start_hand_mock, winning_players_mock):
        match = await self.create_match()
        winning_players_mock.return_value = [match.table.players[1]]
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 17, 10, 10], [player.balance for player in table.players])
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_distribute_pot_several_winners(self, start_hand_mock, winning_players_mock):
        match = await self.create_match()
        winning_players_mock.return_value = match.table.players[1:]
        await match.show_down()
        table = await Table.load_by_name(match.table.name)
        self.assertEqual([10, 13, 12, 12], [player.balance for player in table.players])
        start_hand_mock.assert_called_once_with(ANY)

    @patch('pokerserver.models.match.determine_winning_players')
    @patch('pokerserver.models.match.Match.start_hand', side_effect=return_done_future())
    @gen_test
    async def test_reset(self, _, winning_players_mock):
        match = await self.create_match()
        winning_players_mock.return_value = [match.table.players[1]]
        await match.show_down()

        table = await Table.load_by_name(match.table.name)
        self.assertEqual(1, len(table.pots))
        self.assertEqual(0, table.pots[0].amount)
        for player in table.players:
            self.assertEqual(0, player.bet)
            self.assertEqual(PlayerState.PLAYING, player.state)

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
