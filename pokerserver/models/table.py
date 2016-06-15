from pokerserver.database.tables import TablesTable


class Table:
    def __init__(self, name, max_player_count, players):
        self.name = name
        self.max_player_count = max_player_count
        self.players = players

    @classmethod
    def load_all(cls):
        return [Table(**data) for data in TablesTable.load_all()]
