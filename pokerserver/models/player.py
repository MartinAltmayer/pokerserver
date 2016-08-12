from datetime import datetime
from pokerserver.database import PlayersRelation

PLAYER_NAME_PATTERN = "[A-Za-z0-9]{3,}"


class PlayerNotFoundError(Exception):
    pass


class Player:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, table_id, position, name, balance, cards, bet, last_seen=None, has_folded=False):  # pylint: disable=too-many-arguments
        self.table_id = table_id
        self.position = position
        self.name = name
        self.balance = balance
        self.cards = cards
        self.bet = bet
        self.last_seen = last_seen if last_seen is not None else datetime.now()
        self.has_folded = has_folded

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.__dict__ == other.__dict__

    def to_dict(self, show_cards=False):
        return {
            'table_id': self.table_id,
            'position': self.position,
            'name': self.name,
            'balance': self.balance,
            'cards': self.cards if show_cards else [],
            'bet': self.bet,
            'has_folded': self.has_folded
        }

    @classmethod
    async def load_by_name(cls, name):
        player = await PlayersRelation.load_by_name(name)
        if player is not None:
            return Player(**player)
        else:
            raise PlayerNotFoundError()

    @classmethod
    async def load_if_exists(cls, name):
        return await PlayersRelation.load_by_name(name)

    @classmethod
    async def add_player(cls, table, position, name, balance):  # pylint: disable=too-many-arguments
        await PlayersRelation.add_player(
            table.table_id, position, name, balance,
            cards=[], bet=0, last_seen=datetime.now(), has_folded=False
        )

    @classmethod
    async def load_by_table_id(cls, table_id):
        players = await PlayersRelation.load_by_table_id(table_id)
        return [cls(**player) for player in players]

    @classmethod
    def is_valid_name(cls, name):
        return name.isalpha()

    async def increase_bet(self, amount):
        assert amount > 0, 'Need to increase bet by more than 0.'
        assert amount <= self.balance, 'Trying to bet more than remaining balance.'
        await PlayersRelation.set_balance_and_bet(self.name, self.balance - amount, self.bet + amount)
        self.balance -= amount
        self.bet += amount

    async def set_balance(self, balance):
        assert balance >= 0, 'Insufficient balance.'
        await PlayersRelation.set_balance(self.name, balance)
        self.balance = balance

    async def set_cards(self, cards):
        assert len(cards) <= 2
        await PlayersRelation.set_cards(self.name, cards)
        self.cards = cards

    async def fold(self):
        self.has_folded = True
        await PlayersRelation.set_has_folded(self.name, True)
