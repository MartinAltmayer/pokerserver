from unittest.mock import patch

from tornado.testing import gen_test

from pokerserver.database import PlayerState, TableConfig
from pokerserver.models import Match, Player, Round, Table, get_all_cards
from tests.utils import IntegrationTestCase, create_table


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

    @gen_test
    async def test_pay_blinds(self):
        table_id = 1
        balance = 100
        players = [
            Player(table_id, 1, 'small_blind', balance, [], 0),
            Player(table_id, 2, 'big_blind', balance, [], 0),
            Player(table_id, 3, 'no_blind', balance, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players)
        match = Match(table)

        await match.pay_blinds(players[0], players[1])

        small_blind_player = await Player.load_by_name(players[0].name)
        self.assertEqual(99, small_blind_player.balance)
        self.assertEqual(1, small_blind_player.bet)
        self.assertEqual(PlayerState.PLAYING, small_blind_player.state)

        big_blind_player = await Player.load_by_name(players[1].name)
        self.assertEqual(98, big_blind_player.balance)
        self.assertEqual(2, big_blind_player.bet)
        self.assertEqual(PlayerState.PLAYING, big_blind_player.state)

        table = await Table.load_by_name(table.name)
        self.assertEqual(1, len(table.pots))
        self.assertEqual(3, table.pots[0].amount)
        self.assertEqual({1, 2}, table.pots[0].positions)

    @gen_test
    async def test_pay_blinds_small_blind_all_in(self):
        table_id = 1
        small_blind_balance = 1
        big_blind_balance = 3
        dealer_balance = 3
        players = [
            Player(table_id, 1, 'small_blind', small_blind_balance, [], 0),
            Player(table_id, 2, 'big_blind', big_blind_balance, [], 0),
            Player(table_id, 3, 'no_blind', dealer_balance, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players)
        players = sorted(table.players, key=lambda player: player.position)
        match = Match(table)

        await match.pay_blinds(players[0], players[1])

        small_blind_player = await Player.load_by_name(players[0].name)
        self.assertEqual(0, small_blind_player.balance)
        self.assertEqual(1, small_blind_player.bet)
        self.assertEqual(PlayerState.ALL_IN, small_blind_player.state)

        big_blind_player = await Player.load_by_name(players[1].name)
        self.assertEqual(1, big_blind_player.balance)
        self.assertEqual(2, big_blind_player.bet)
        self.assertEqual(PlayerState.PLAYING, big_blind_player.state)

        table = await Table.load_by_name(table.name)
        self.assertEqual(2, len(table.pots))
        self.assertEqual(2, table.pots[0].amount)
        self.assertEqual({1, 2}, table.pots[0].positions)
        self.assertEqual(1, table.pots[1].amount)
        self.assertEqual({2}, table.pots[1].positions)

    @gen_test
    async def test_pay_blinds_big_blind_all_in(self):
        table_id = 1
        small_blind_balance = 3
        big_blind_balance = 1
        dealer_balance = 3
        players = [
            Player(table_id, 1, 'small_blind', small_blind_balance, [], 0),
            Player(table_id, 2, 'big_blind', big_blind_balance, [], 0),
            Player(table_id, 3, 'no_blind', dealer_balance, [], 0)
        ]
        table = await create_table(table_id=table_id, players=players)
        match = Match(table)

        await match.pay_blinds(players[0], players[1])

        small_blind_player = await Player.load_by_name(players[0].name)
        self.assertEqual(2, small_blind_player.balance)
        self.assertEqual(1, small_blind_player.bet)
        self.assertEqual(PlayerState.PLAYING, small_blind_player.state)

        big_blind_player = await Player.load_by_name(players[1].name)
        self.assertEqual(0, big_blind_player.balance)
        self.assertEqual(1, big_blind_player.bet)
        self.assertEqual(PlayerState.ALL_IN, big_blind_player.state)

        table = await Table.load_by_name(table.name)
        self.assertEqual(1, len(table.pots))
        self.assertEqual(2, table.pots[0].amount)
        self.assertEqual({1, 2}, table.pots[0].positions)

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
        expected_dealer = table.get_player_at(2)
        expected_small_blind = table.get_player_at(3)
        expected_big_blind = table.get_player_at(1)
        self.assertEqual(expected_dealer, table.dealer)
        self.assertEqual(expected_dealer, table.current_player)
        self.assertEqual(10, expected_dealer.balance)
        self.assertEqual(9, expected_small_blind.balance)
        self.assertEqual(8, expected_big_blind.balance)
        self.assertEqual(0, expected_dealer.bet)
        self.assertEqual(1, expected_small_blind.bet)
        self.assertEqual(2, expected_big_blind.bet)
        for player in table.players:
            self.assertEqual(2, len(player.cards))
        self.assertEqual(46, len(table.remaining_deck))
        self.assertEqual([], table.open_cards)
