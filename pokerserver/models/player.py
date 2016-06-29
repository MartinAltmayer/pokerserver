from pokerserver.database import PlayersRelation


class PlayerNotFoundError(Exception):
    pass


class Player:
    def __init__(self, table_id, position, name, balance, cards, bet):  # pylint: disable=too-many-arguments
        self.table_id = table_id
        self.position = position
        self.name = name
        self.balance = balance
        self.cards = cards
        self.bet = bet

    def to_dict(self):
        return {
            'table_id': self.table_id,
            'position': self.position,
            'name': self.name,
            'balance': self.balance,
            'cards': self.cards,
            'bet': self.bet
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
    async def add_player(cls, table, position, name, balance, cards, bet):  # pylint: disable=too-many-arguments
        await PlayersRelation.add_player(table.table_id, position, name, balance, cards, bet)

    @classmethod
    async def load_by_table_id(cls, table_id):
        players = await PlayersRelation.load_by_table_id(table_id)
        return [cls(**player) for player in players]

    @classmethod
    def is_valid_name(cls, name):
        return name.isalpha()