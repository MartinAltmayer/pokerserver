import textwrap

from pokerserver.database.database import Database


class StatsTable:
    NAME = 'stats'
    CREATE_QUERY = textwrap.dedent("""
        CREATE TABLE stats (
            player_name VARCHAR,
            matches INT,
            buy_in INT,
            gain INT,
            PRIMARY KEY (player_name)
        )
    """)

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
    async def increment_stats(cls, player_name, matches, buy_in, gain):
        db = Database.instance()
        await db.execute("""
            UPDATE stats
            SET matches = matches + ?, buy_in = buy_in + ?, gain = gain + ?
            WHERE player_name = ?
            """, matches, buy_in, gain, player_name)
