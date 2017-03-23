from collections import Counter
from functools import partial

from .card import parse_card, MAX_RANK, MIN_RANK


def find_high_card(cards):
    return _find_high_card(cards, 5)


def _find_high_card(cards, number):
    return sorted([card.rank for card in cards], reverse=True)[:number]


def find_n_of_a_kind(n, cards):
    counter = Counter(card.rank for card in cards)
    _, count = counter.most_common(1)[0]
    if count >= n:
        rank = sort_counter(counter)[0]
        remaining_cards = [card for card in cards if card.rank != rank]
        return [rank] + _find_high_card(remaining_cards, 5 - n)

    return None


def find_two_pairs(cards):
    counter = Counter(card.rank for card in cards)
    _, (_, count2) = counter.most_common(2)
    if count2 >= 2:
        rank1, rank2 = sort_counter(counter)[:2]
        remaining_cards = [card for card in cards if card.rank not in (rank1, rank2)]
        return [rank1, rank2] + _find_high_card(remaining_cards, 1)

    return None


def find_straight(cards):
    ranks = sorted({card.rank for card in cards}, reverse=True)
    if ranks[0] == MAX_RANK:
        ranks.append(MIN_RANK - 1)  # ace can be appended at top and bottom
    for i, rank in enumerate(ranks[:-5 + 1]):
        possible_straight = ranks[i:i + 5]
        if all(v + i == rank for i, v in enumerate(possible_straight)):
            return rank

    return None


def find_flush(cards):
    flush_cards = _find_flush_cards(cards)
    if flush_cards is not None:
        return find_high_card(flush_cards)
    return None


def _find_flush_cards(cards):
    counter = Counter(card.suit for card in cards)
    suit, count = counter.most_common(1)[0]
    if count >= 5:
        return [card for card in cards if card.suit == suit]
    return None


def find_full_house(cards):
    counter = Counter(card.rank for card in cards)
    if 3 in counter.values() and 2 in counter.values():
        return sort_counter(counter)
    return None


def find_straight_flush(cards):
    flush_cards = _find_flush_cards(cards)
    return find_straight(flush_cards) if flush_cards is not None else None


def sort_counter(counter):
    ranks_and_counts = counter.most_common()
    ranks_and_counts.sort(key=lambda t: (t[1], t[0]), reverse=True)   # sort cards with same count by rank
    card_count = 0
    for i, (_, count) in enumerate(ranks_and_counts):
        card_count += count
        if card_count >= 5:
            return [r for r, _ in ranks_and_counts[:i + 1]]

    return [r for r, _ in ranks_and_counts]


RANKING_FUNCTIONS = [
    find_high_card,
    partial(find_n_of_a_kind, 2),
    find_two_pairs,
    partial(find_n_of_a_kind, 3),
    find_straight,
    find_flush,
    find_full_house,
    partial(find_n_of_a_kind, 4),
    find_straight_flush
]

# Reverse after adding indexes: [(8, find_straight_flush), ..., (0, find_high_card)]
_RANKING_FUNCTIONS_WITH_INDEX = list(reversed(list(enumerate(RANKING_FUNCTIONS))))


def rank(cards_strings):
    cards = [parse_card(s) for s in cards_strings]
    for i, rank_function in _RANKING_FUNCTIONS_WITH_INDEX:
        ranking = rank_function(cards)
        if ranking is not None:
            return i, ranking
    # the last ranking function never returns None


def determine_winning_players(active_players, open_cards):
    ranks = {player: rank(player.cards + open_cards) for player in active_players}
    max_rank = max(ranks.values())
    return [player for player in active_players if ranks[player] == max_rank]
