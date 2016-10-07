from unittest.mock import patch
from tornado.testing import gen_test

from pokerserver.database import TableConfig, TablesRelation, PlayersRelation, StatsRelation
from pokerserver.models import Table, Round, get_all_cards

from tests.integration.utils.integration_test import IntegrationHttpTestCase


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

    async def join_table(self):
        # Make Player0 the first dealer
        with patch('random.choice', side_effect=lambda players: players[0]) as choice_mock:
            for player in self.player_data:
                await self.fetch_with_uuid(
                    '/table/{}/join?position={}'.format(self.table.name, player['position']), player)
        self.assertEqual(1, choice_mock.call_count)

    async def fetch_with_uuid(self, url, player):
        uuid = self.uuids[player['name']]
        separator = '&' if '?' in url else '?'
        return await self.fetch_async(url + separator + 'uuid=' + uuid)

    @gen_test
    async def test_all_call_and_check(self):
        await self.async_setup()

        await self.assert_special_players(
            dealer='Player0', small_blind='Player1', big_blind='Player2', current_player='Player3')
        await self.assert_round_and_pot(Round.preflop, 3)
        await self.assert_balances_and_bets([10, 9, 8, 10], [0, 1, 2, 0])

        await self.everyone_calls(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])
        await self.every_one_checks_three_times(player_order=[3, 0, 1, 2], balances=[8, 8, 8, 8])

        await self.assert_round_and_pot(Round.preflop, 3)
        await self.assert_balances_and_bets([16, 8, 7, 6], [0, 0, 1, 2])

        await self.everyone_calls(player_order=[0, 1, 2, 3], balances=[14, 6, 6, 6])
        await self.every_one_checks_three_times(player_order=[0, 1, 2, 3], balances=[14, 6, 6, 6])

        await self.assert_round_and_pot(Round.preflop, 3)
        await self.assert_balances_and_bets([20, 6, 6, 5], [2, 0, 0, 1])

        await self.everyone_calls(player_order=[1, 2, 3, 0], balances=[20, 4, 4, 4])
        await self.every_one_checks_three_times(player_order=[1, 2, 3, 0], balances=[20, 4, 4, 4])

        await self.assert_round_and_pot(Round.preflop, 3)
        await self.assert_balances_and_bets([27, 2, 4, 4], [1, 2, 0, 0])

        await self.everyone_calls(player_order=[2, 3, 0, 1], balances=[26, 2, 2, 2])
        await self.every_one_checks_three_times(player_order=[2, 3, 0, 1], balances=[26, 2, 2, 2])

        await self.assert_round_and_pot(Round.preflop, 3)
        await self.assert_balances_and_bets([34, 1, 0, 2], [0, 1, 2, 0])

        await self.everyone_calls(player_order=[3, 0, 1, 2], balances=[32, 0, 0, 0])
        await self.every_one_checks_three_times(player_order=[3, 0, 1, 2], balances=[32, 0, 0, 0])

        table = await Table.load_by_name(self.table.name)
        self.assertTrue(table.is_closed)

        stats = await StatsRelation.get_stats()
        self.assertEqual({
            'Player0': 40,
            'Player1': 0,
            'Player2': 0,
            'Player3': 0
        }, stats)

    async def everyone_calls(self, player_order, balances):
        for index in player_order:
            await self.fetch_with_uuid('/table/{}/call'.format(self.table.name), self.player_data[index])

        await self.assert_round_and_pot(Round.flop, 8)
        await self.assert_balances_and_bets(balances, [0, 0, 0, 0])

    async def every_one_checks_three_times(self, player_order, balances):
        for index in player_order:
            await self.fetch_with_uuid('/table/{}/check'.format(self.table.name), self.player_data[index])

        await self.assert_round_and_pot(Round.turn, 8)
        await self.assert_balances_and_bets(balances, [0, 0, 0, 0])

        for index in player_order:
            await self.fetch_with_uuid('/table/{}/check'.format(self.table.name), self.player_data[index])

        await self.assert_round_and_pot(Round.river, 8)
        await self.assert_balances_and_bets(balances, [0, 0, 0, 0])

        for index in player_order:
            await self.fetch_with_uuid('/table/{}/check'.format(self.table.name), self.player_data[index])

    async def assert_special_players(self, dealer=None, small_blind=None,
                                     big_blind=None, current_player=None):
        table = await TablesRelation.load_table_by_id(self.table.table_id)
        if dealer is not None:
            self.assertEqual(dealer, table['dealer'])
        if small_blind is not None:
            self.assertEqual(small_blind, table['small_blind_player'])
        if big_blind is not None:
            self.assertEqual(big_blind, table['big_blind_player'])
        if current_player is not None:
            self.assertEqual(current_player, table['current_player'])

    async def assert_round_and_pot(self, round_of_match, main_pot):
        table = await Table.load_by_name(self.table.name)
        self.assertEqual(round_of_match, table.round)
        self.assertEqual(main_pot, table.main_pot)

    async def assert_balances_and_bets(self, balances, bets):
        players = await PlayersRelation.load_by_table_id(self.table.table_id)
        players.sort(key=lambda player: player['position'])

        for player, balance, bet in zip(players, balances, bets):
            self.assertEqual(balance, player['balance'],
                             msg='Unexpected balance for {}'.format(player['name']))
            self.assertEqual(bet, player['bet'],
                             msg='Unexpected bet for {}'.format(player['name']))
