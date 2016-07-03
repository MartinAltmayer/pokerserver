RANKS = tuple([str(i) for i in range(2, 11)] + ['J', 'D', 'K', 'A'])
SUITS = ('s', 'h', 'd', 'c')


def split_card(string):
    return string[:-1], string[-1:]


def is_valid_card(string):
    rank, suit = split_card(string)
    return rank in RANKS and suit in SUITS


def get_all_cards():
    return [rank + suit for rank in RANKS for suit in SUITS]
