from collections import namedtuple

from .database import Database
from .relation import Relation


class StatisticsRelation(Relation):
    NAME = 'statistics'

    FIELDS = [
        'player_name',
        'matches',
        'buy_in',
        'gain'
    ]

    STATISTICS_RELATION_ROW = namedtuple('StatisticsRelationRow', FIELDS)

    CREATE_QUERY = """
        CREATE TABLE statistics (
            player_name VARCHAR,
            matches INT,
            buy_in INT,
            gain INT,
            PRIMARY KEY (player_name)
        )
    """

    DROP_IF_EXISTS_QUERY = """
        DROP TABLE IF EXISTS statistics
    """

    LOAD_ALL_QUERY = """
        SELECT {} FROM statistics
    """.format(','.join(FIELDS))

    CLEAR_QUERY = """
        DELETE FROM statistics
    """

    INIT_STATS_QUERY = """
        INSERT INTO statistics ({}) VALUES ({})
    """.format(','.join(FIELDS), ','.join(['?'] * len(FIELDS)))

    INCREMENT_STATS_QUERY = """
        UPDATE statistics
        SET matches = matches + ?, buy_in = buy_in + ?, gain = gain + ?
        WHERE player_name = ?
    """

    @classmethod
    async def load_all(cls):
        statistics_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_ALL_QUERY) as cursor:
            async for row in cursor:
                statistics_data.append(cls._from_db(row))
        return statistics_data

    @classmethod
    def _from_db(cls, row):
        return cls.STATISTICS_RELATION_ROW(*row)._asdict()

    @classmethod
    async def init_statistics(cls, player_name, matches=0, buy_in=0, gain=0):
        await Database.instance().execute(cls.INIT_STATS_QUERY, player_name, matches, buy_in, gain)

    @classmethod
    async def increment_statistics(cls, player_name, matches, buy_in, gain):
        db = Database.instance()
        result = await db.execute(cls.INCREMENT_STATS_QUERY, matches, buy_in, gain, player_name)
        if result.rowcount == 0:
            await db.execute(cls.INIT_STATS_QUERY, player_name, matches, buy_in, gain)
