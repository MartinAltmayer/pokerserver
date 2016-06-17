from pokerserver.database.database import Database


class TablesTable:
    NAME = 'tables'
    CREATE_QUERY = """
        CREATE TABLE tables (
            id INTEGER PRIMARY KEY,
            name VARCHAR UNIQUE,
            max_player_count INT,
            players VARCHAR
        )
    """

    @classmethod
    async def load_all(cls):
        table_data = []
        db = Database.instance()
        async with db.execute("""
                SELECT name, max_player_count, players
                FROM tables
                ORDER BY id
                """) as cursor:
            async for row in cursor:
                name, max_player_count, players = row
                players = players.split(',')
                table_data.append({
                    'name': name,
                    'max_player_count': max_player_count,
                    'players': players
                })

        return table_data

    @classmethod
    async def create_table(cls, name, max_player_count, players):
        players = ','.join(players)
        db = Database.instance()
        await db.execute(
            'INSERT INTO tables (name, max_player_count, players) VALUES (?,?,?)',
            name, max_player_count, players
        )
