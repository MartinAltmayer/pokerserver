# pylint: disable=no-self-use
from unittest import TestCase
from unittest.mock import Mock

from pokerserver.models.card import parse_card
from pokerserver.models.ranking import (
    find_high_card, find_n_of_a_kind, find_two_pairs, find_straight, find_flush,
    find_full_house, find_straight_flush, rank as rank_function, determine_winning_players
)


class TestRanking(TestCase):
    def parse_cards(self, card_strings):
        return [parse_card(s) for s in card_strings]

    def test_find_high_card(self):
        cards = self.parse_cards(['5d', 'Jh', 'As', '10c', '2c', '2d', '4d'])
        self.assertEqual([14, 11, 10, 5, 4], find_high_card(cards))

    def test_find_n_of_a_kind(self):
        cards = self.parse_cards(['5d', 'Jh', 'As', '10c', '2c', '2d', '4d'])
        self.assertEqual([2, 14, 11, 10], find_n_of_a_kind(2, cards))

        cards = self.parse_cards(['5d', 'Jh', 'As', '10c', '2c', '3d', '4d'])
        self.assertIsNone(find_n_of_a_kind(2, cards))

        cards = self.parse_cards(['5d', 'Jh', 'As', '10c', '5c', '5d', '5d'])
        self.assertEqual([5, 14], find_n_of_a_kind(4, cards))

    def test_find_two_pairs(self):
        cards = self.parse_cards(['5d', 'Jh', 'As', '5c', '2c', '2d', '4d'])
        self.assertEqual([5, 2, 14], find_two_pairs(cards))

        cards = self.parse_cards(['5d', 'Jh', 'As', '5c', '2c', '3d', '4d'])
        self.assertIsNone(find_two_pairs(cards))

    def test_find_straight(self):
        cards = self.parse_cards(['4d', '8h', '3s', '5c', '7c', '6d', 'Qd'])
        self.assertEqual(8, find_straight(cards))

        cards = self.parse_cards(['4d', '7h', '3s', '5c', '7c', '6d', 'Qd'])
        self.assertEqual(7, find_straight(cards))

        cards = self.parse_cards(['4d', '7h', '2s', '5c', '7c', '6d', 'Qd'])
        self.assertIsNone(find_straight(cards))

    def test_find_straight_low_ace(self):
        cards = self.parse_cards(['4d', '8h', '3s', '5c', '2c', '7d', 'Ad'])
        self.assertEqual(5, find_straight(cards))

        # don't use low ace if better straight possible
        cards = self.parse_cards(['4d', '8h', '3s', '5c', '2c', '6d', 'Ad'])
        self.assertEqual(6, find_straight(cards))

        # 'low king' is not allowed
        cards = self.parse_cards(['Kd', '8h', '3s', '4c', '2c', '7d', 'Ad'])
        self.assertIsNone(find_straight(cards))

    def test_find_flush(self):
        cards = self.parse_cards(['10d', '8d', '3d', '5d', 'Qd', '7d', 'As'])
        self.assertEqual([12, 10, 8, 7, 5], find_flush(cards))

        cards = self.parse_cards(['10d', '8d', '3c', '5h', 'Qd', '7d', 'As'])
        self.assertIsNone(find_flush(cards))

    def test_find_full_house(self):
        cards = self.parse_cards(['10d', '10s', '3d', '5d', '3h', '3c', 'As'])
        self.assertEqual([3, 10], find_full_house(cards))

        # choose best full house
        cards = self.parse_cards(['10d', '10s', '3d', 'Qd', '3h', '3c', 'Qs'])
        self.assertEqual([3, 12], find_full_house(cards))

        cards = self.parse_cards(['10d', '10s', '3c', '10h', 'Qd', '7d', 'As'])
        self.assertIsNone(find_full_house(cards))

        cards = self.parse_cards(['10d', '10s', '3c', '3h', 'Qd', '7d', 'As'])
        self.assertIsNone(find_full_house(cards))

    def test_find_straight_flush(self):
        cards = self.parse_cards(['2d', '3d', '4d', '5d', '6d', '7d', '8c'])
        self.assertEqual(7, find_straight_flush(cards))

        # low ace
        cards = self.parse_cards(['2d', '3d', '4d', '5d', '6c', '7c', 'Ad'])
        self.assertEqual(5, find_straight_flush(cards))

        # straight, no flush
        cards = self.parse_cards(['2d', '3d', '4s', '5c', '6d', '7d', '8d'])
        self.assertIsNone(find_straight_flush(cards))

        # flush, no straight
        cards = self.parse_cards(['10d', '10d', '3d', '3d', 'Qd', '7d', 'Ad'])
        self.assertIsNone(find_straight_flush(cards))

    def test_ranking(self):
        # In particular check cases where two rankings apply (e.g. Full House and Flush)
        card_sets = [
            # Straight Flush
            ['As', 'Ks', 'Qs', 'Js', '10s', '2c', '3c'],
            ['Ks', 'Qs', 'Js', '10s', '9s', '2c', '3c'],
            # 4 of a kind
            ['10s', '10d', '10c', '10h', 'As', '2c', '2d'],
            ['10s', '10d', '10c', '10h', 'Ks', '2c', '2d'],
            # Full House
            ['As', 'Ad', 'Ah', 'Kh', 'Ks', '2c', '2d'],
            ['3s', '3d', '3h', 'Kh', 'Ks', '2c', '2d'],
            # Flush
            ['3s', 'Ks', '4s', '10s', '7s', '2c', '2d'],
            ['3s', 'Qs', '4s', '10s', '7s', '2c', '2d'],
            # Straight
            ['3s', '4d', '5h', '6d', '7c', '2c', '2d'],
            ['As', '2c', '3s', '4d', '5h', '7c', '2d'],
            # 3 of a kind
            ['10s', '10d', '10c', 'Ah', 'Ks', '3c', '2d'],
            ['10s', '10d', '10c', 'Ah', 'Qs', '3c', '2d'],
            # Two Pairs
            ['10s', '10d', 'Kh', '4c', '4c', '2h', '6d'],
            ['10s', '10d', 'Ah', '3c', '3c', '2h', '6d'],
            ['10s', '10d', '4h', '3c', '3c', '2h', '6d'],
            # 2 of a kind
            ['10s', '10d', 'Ah', '4c', '5c', '2h', '6d'],
            ['10s', '10d', 'Kh', '3c', '5c', '2h', '6d'],
            # High card
            ['Qs', '10d', 'Ah', '3c', '5c', '2h', '6d'],
            ['Qs', '10d', 'Kh', '3c', '5c', '2h', '6d'],
        ]

        ranks = [rank_function(c) for c in card_sets]
        for rank, card_set in zip(ranks, card_sets):
            print(rank, card_set)

        sorted_card_sets = sorted(card_sets, key=rank_function, reverse=True)
        self.assertListEqual(card_sets, sorted_card_sets)

    def test_determine_winning_players_single(self):
        open_cards = ['2c', '3c', '5c', '6d', '7d']
        active_players = [Mock(cards=['Ac', 'Kc']), Mock(cards=['Kh', 'Qh'])]

        winning_players = determine_winning_players(active_players, open_cards)
        self.assertEqual([active_players[0]], winning_players)

    def test_determine_winning_players_multiple(self):
        open_cards = ['2c', '3c', '5c', '6c', '7d']
        active_players = [Mock(cards=['As', 'Ks']), Mock(cards=['Ah', 'Kh'])]

        winning_players = determine_winning_players(active_players, open_cards)
        self.assertEqual(set(active_players), set(winning_players))
