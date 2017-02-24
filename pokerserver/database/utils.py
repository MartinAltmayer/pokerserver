def make_card_list(cards):
    return ','.join(cards)


def from_card_list(card_list_string):
    return card_list_string.split(',') if card_list_string else []


def to_pot_list_string(pot_dicts):
    """
    :param pot_dicts: list of dicts representing the separate pots
    :return: string of the form "<pot 1>;<pot 2>;..." with <pot 1> = <position 1>:<bet 1>,<position 2>:<bet 2>
    """

    pot_dicts = pot_dicts or []

    def to_string(bets):
        return ['{}:{}'.format(position, bet) for position, bet in bets.items()]

    return ';'.join(','.join(to_string(pot['bets'])) for pot in pot_dicts)


def from_pot_list_string(pot_list_string):
    """
    :param pot_list_string: "<pot 1>;<pot 2>;..." with <pot 1> = <position 1>:<bet 1>,<position 2>:<bet 2>
    :return: list of dicts representing the separate pots
    """

    if not pot_list_string:
        return [
            {
                'bets': {}
            }
        ]

    pot_strings = pot_list_string.split(';')

    def to_dict(pot_string):
        bets = [bets_string.split(":") for bets_string in pot_string.split(',') if bets_string]
        return {
            'bets': {int(position): int(bet or 0) for position, bet in bets}
        }

    return [to_dict(pot_string) for pot_string in pot_strings] if pot_list_string else []
