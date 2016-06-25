from pokerserver.database import PlayersRelation


class Player:
    def __init__(self, table_id, position, name, balance, cards, bet):
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
    async def load_by_table_id(cls, table_id):
        players = await PlayersRelation.load_by_table_id(table_id)
        return [cls(**player) for player in players]
