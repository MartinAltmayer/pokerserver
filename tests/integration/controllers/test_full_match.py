from unittest.mock import patch

from tornado.testing import gen_test

from pokerserver.database import PlayersRelation, TableConfig, TablesRelation
from pokerserver.models import Round, Statistics, Table, get_all_cards
from tests.utils import IntegrationHttpTestCase


class TestFullMatch(IntegrationHttpTestCase):
    player_data = [
        {'name': 'Player0', 'position': 2},
        {'name': 'Player1', 'position': 4},
        {'name': 'Player2', 'position': 6},
        {'name': 'Player3', 'position': 8},
    ]

    async def async_setup(self):
        patcher = patch('random.shuffle', side_effect=self.fake_shuffle)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.table = await self.create_table()
        self.uuids = await self.fetch_uuids()
        await self.join_table()

    @staticmethod
    def fake_shuffle(cards):
        # First two cards are for Player0, who will consequently win each hand.
        player_cards = ['As', 'Ah', '2c', '2d', '2h', '2s', '3h', '3c']
        community_cards = ['4c', '4h', '5c', '5h', '6c']
        fixed_cards = player_cards + community_cards
        remaining_cards = [card for card in get_all_cards() if card not in fixed_cards]

        cards.clear()
        cards[0:0] = remaining_cards + list(reversed(fixed_cards))  # cards are distributed from the end

    async def create_table(self):
        config = TableConfig(
            min_player_count=4,
            max_player_count=8,
            small_blind=1,
            big_blind=2,
            start_balance=10
        )
        await Table.create_tables(1, config)
        tables = await Table.load_all()
        return tables[0]

    async def fetch_uuids(self):
        uuids = {}
        for player in self.player_data:
            response = await self.fetch_async('/uuid?player_name={}'.format(player['name']))
            uuids[player['name']] = response.body.decode('ascii')
        return uuids

    def get_uuid(self, player):
        return self.uuids[player['name']]

    async def join_table(self):
        # Make Player0 the first dealer
        with patch('random.choice', side_effect=lambda players: players[0]) as choice_mock:
            for player in self.player_data:
                await self.post_with_uuid(
                    '/table/{}/actions/join'.format(self.table.name),
                    self.get_uuid(player),
                    body={'position': player['position']}
                )
        self.assertEqual(1, choice_mock.call_count)

    @gen_test
    async def test_all_call_and_check(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._everyone_checks_three_times(player_order=[1, 2, 3, 0], balances=[8, 8, 8, 8])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([16, 8, 7, 6], [0, 0, 1, 2])

        await self._everyone_calls_and_big_blind_checks(player_order=[0, 1, 2, 3], balances=[14, 6, 6, 6])
        await self._everyone_checks_three_times(player_order=[2, 3, 0, 1], balances=[14, 6, 6, 6])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([20, 6, 6, 5], [2, 0, 0, 1])

        await self._everyone_calls_and_big_blind_checks(player_order=[1, 2, 3, 0], balances=[20, 4, 4, 4])
        await self._everyone_checks_three_times(player_order=[3, 0, 1, 2], balances=[20, 4, 4, 4])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([27, 2, 4, 4], [1, 2, 0, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[2, 3, 0, 1], balances=[26, 2, 2, 2])
        await self._everyone_checks_three_times(player_order=[0, 1, 2, 3], balances=[26, 2, 2, 2])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([34, 1, 0, 2], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[32, 0, 0, 0])
        await self._everyone_checks_three_times(player_order=[1, 2, 3, 0], balances=[32, 0, 0, 0])

        table = await Table.load_by_name(self.table.name)
        self.assertTrue(table.is_closed)

        stats = await Statistics.load()
        self.assertEqual({
            'Player0': {'matches': 1, 'buy_in': 10, 'gain': 40},
            'Player1': {'matches': 1, 'buy_in': 10, 'gain': 0},
            'Player2': {'matches': 1, 'buy_in': 10, 'gain': 0},
            'Player3': {'matches': 1, 'buy_in': 10, 'gain': 0}
        }, {statistics.player_name: statistics.to_dict() for statistics in stats.player_statistics})

    @gen_test
    async def test_everyone_folds_preflop(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_folds(player_order=[3, 0, 1])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 10, 8], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_flop_except_dealer(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1, 2, 3])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([16, 8, 7, 6], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_flop_except_big_blind(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1])
        await self._player_raises(2)
        await self._everyone_folds(player_order=[3, 0])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([8, 8, 15, 6], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_turn_except_dealer(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.TURN, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1, 2, 3])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([16, 8, 7, 6], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_turn_except_big_blind(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.TURN, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1])
        await self._player_raises(2)
        await self._everyone_folds(player_order=[3, 0])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([8, 8, 15, 6], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_river_except_dealer(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.TURN, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.RIVER, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1, 2, 3])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([16, 8, 7, 6], [0, 0, 1, 2])

    @gen_test
    async def test_everyone_folds_on_river_except_big_blind(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls_and_big_blind_checks(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.TURN, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_checks(player_order=[1, 2, 3, 0])
        await self._assert_round_and_pots(Round.RIVER, [8])
        await self._assert_balances_and_bets([8, 8, 8, 8], [0, 0, 0, 0])

        await self._everyone_folds(player_order=[1])
        await self._player_raises(2)
        await self._everyone_folds(player_order=[3, 0])

        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([8, 8, 15, 6], [0, 0, 1, 2])

    @gen_test
    async def test_big_blind_should_not_make_another_turn_after_raise(self):
        await self.async_setup()

        await self._assert_special_players(dealer='Player0', current_player='Player3')
        await self._assert_round_and_pots(Round.PREFLOP, [3])
        await self._assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self._everyone_calls(player_order=[3, 0, 1])
        await self._player_raises(2)
        await self._everyone_calls(player_order=[3, 0, 1])

        await self._assert_round_and_pots(Round.FLOP, [12])
        await self._assert_balances_and_bets([7, 7, 7, 7], [0, 0, 0, 0])

    async def _player_raises(self, index):
        await self.post_with_uuid(
            '/table/{}/actions/raise'.format(self.table.name),
            self.get_uuid(self.player_data[index]),
            body={'amount': 1}
        )

    async def _everyone_calls_and_big_blind_checks(self, player_order, balances):
        await self._everyone_calls(player_order[:-1])
        await self._everyone_checks(player_order[-1:])
        await self._assert_round_and_pots(Round.FLOP, [8])
        await self._assert_balances_and_bets(balances, [0, 0, 0, 0])

    async def _everyone_checks_three_times(self, player_order, balances):
        await self._everyone_checks(player_order)

        await self._assert_round_and_pots(Round.TURN, [8])
        await self._assert_balances_and_bets(balances, [0, 0, 0, 0])

        await self._everyone_checks(player_order)

        await self._assert_round_and_pots(Round.RIVER, [8])
        await self._assert_balances_and_bets(balances, [0, 0, 0, 0])

        await self._everyone_checks(player_order)

    async def _everyone_checks(self, player_order):
        for index in player_order:
            await self.post_with_uuid(
                '/table/{}/actions/check'.format(self.table.name),
                self.get_uuid(self.player_data[index])
            )

    async def _everyone_calls(self, player_order):
        for index in player_order:
            await self.post_with_uuid(
                '/table/{}/actions/call'.format(self.table.name),
                self.get_uuid(self.player_data[index])
            )

    async def _everyone_folds(self, player_order):
        for index in player_order:
            print(index)
            await self.post_with_uuid(
                '/table/{}/actions/fold'.format(self.table.name),
                self.get_uuid(self.player_data[index])
            )

    async def _assert_special_players(self, dealer=None, current_player=None):
        table = await TablesRelation.load_table_by_id(self.table.table_id)
        if dealer is not None:
            self.assertEqual(dealer, table['dealer'])
        if current_player is not None:
            self.assertEqual(current_player, table['current_player'])

    async def _assert_round_and_pots(self, round_of_match, pots):
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(round_of_match, table.round)
        self.assertEqual(pots, [pot.amount for pot in table.pots])

    async def _assert_balances_and_bets(self, balances, bets):
        players = await PlayersRelation.load_by_table_id(self.table.table_id)
        players.sort(key=lambda player: player['position'])

        for player, balance, bet in zip(players, balances, bets):
            self.assertEqual(balance, player['balance'],
                             msg='Unexpected balance for {}'.format(player['name']))
            self.assertEqual(bet, player['bet'],
                             msg='Unexpected bet for {}'.format(player['name']))
