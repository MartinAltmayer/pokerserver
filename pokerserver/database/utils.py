def make_card_list(cards):
    return ','.join(cards)


def from_card_list(card_list_string):
    return card_list_string.split(',') if card_list_string else []


def make_int_list(ints):
    return ','.join(str(i) for i in ints)


def from_int_list(int_list_string):
    return [int(s) for s in int_list_string.split(',')] if int_list_string else []
