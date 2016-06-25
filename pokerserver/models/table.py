from pokerserver.database.tables import TablesRelation


class Table:
    def __init__(self, name, max_player_count, players):
        self.name = name
        self.max_player_count = max_player_count
        self.players = players

    @classmethod
    async def load_all(cls):
        tables = await TablesRelation.load_all()
        return [Table(**data) for data in tables]

    @classmethod
    async def create_tables(cls, number, max_player_count):
        table_names = await cls._get_unused_table_names(number)
        for name in table_names:
            await TablesRelation.create_table(name, max_player_count, [])

    def is_free(self):
        return len(self.players) < self.max_player_count

    def to_dict(self):
        return {
            'name': self.name,
            'max_player_count': self.max_player_count,
            'players': self.players
        }

    @classmethod
    async def _get_unused_table_names(cls, number):
        tables = await cls.load_all()
        used_names = {table.name for table in tables}
        found_names = []
        i = 1
        while len(found_names) < number:
            name = 'Table {}'.format(i)
            if name not in used_names:
                found_names.append(name)
            i += 1

        return found_names
