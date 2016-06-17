from pokerserver.database.tables import TablesTable


class Table:
    def __init__(self, name, max_player_count, players):
        self.name = name
        self.max_player_count = max_player_count
        self.players = players

    @classmethod
    async def load_all(cls):
        tables = await TablesTable.load_all()
        return [Table(**data) for data in tables]

    def to_dict(self):
        return {
            'name': self.name,
            'max_player_count': self.max_player_count,
            'players': self.players
        }
