from .database import Database


class StatsRelation:
    NAME = 'stats'
    CREATE_QUERY = """
        CREATE TABLE stats (
            player_name VARCHAR,
            matches INT,
            buy_in INT,
            gain INT,
            PRIMARY KEY (player_name)
        )
    """

    INIT_STATS_QUERY = """
        INSERT INTO stats (player_name, matches, buy_in, gain) VALUES (?, ?, ?, ?)
    """

    INCREMENT_STATS_QUERY = """
        UPDATE stats
        SET matches = matches + ?, buy_in = buy_in + ?, gain = gain + ?
        WHERE player_name = ?
    """

    @classmethod
    async def get_stats(cls):
        stats = {}
        db = Database.instance()
        async with db.execute('SELECT player_name, matches, buy_in, gain FROM stats') as cursor:
            async for row in cursor:
                player_name = row[0]
                values = row[1:]
                stats[player_name] = tuple(values)

        return stats

    @classmethod
    async def init_stats(cls, player_name):
        Database.instance().execute(cls.INCREMENT_STATS_QUERY, player_name, 0, 0, 0)

    @classmethod
    async def increment_stats(cls, player_name, matches, buy_in, gain):
        db = Database.instance()
        result = await db.execute(cls.INCREMENT_STATS_QUERY, matches, buy_in, gain, player_name)
        if result.rowcount == 0:
            await db.execute(cls.INIT_STATS_QUERY, player_name, matches, buy_in, gain)
