
def make_card_list(cards):
    return ','.join(cards)


def from_card_list(card_list_string):
    if len(card_list_string) > 0:
        return card_list_string.split(',')
    else:
        return []


def make_int_list(ints):
    return ','.join(str(i) for i in ints)


def from_int_list(int_list_string):
    if len(int_list_string) > 0:
        return [int(s) for s in int_list_string.split(',')]
    else:
        return []
