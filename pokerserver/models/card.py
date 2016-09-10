from collections import namedtuple

RANKS = {
    'A': 14,
    'K': 13,
    'Q': 12,
    'J': 11
}
RANKS.update({str(i): i for i in range(2, 11)})
MAX_RANK = 14
MIN_RANK = 2
SUITS = ('s', 'h', 'd', 'c')


Card = namedtuple('Card', 'rank suit')


def split_card(string):
    rank, suit = string[:-1], string[-1:]
    return rank, suit


def parse_card(string):
    rank, suit = split_card(string)
    return Card(RANKS[rank], suit)


def is_valid_card(string):
    rank, suit = split_card(string)
    return rank in RANKS and suit in SUITS


def get_all_cards():
    return [rank + suit for rank in RANKS for suit in SUITS]
