from collections import namedtuple

from pokerserver.database import Database


class PlayersRelation:
    NAME = 'players'

    FIELDS = ['table_id', 'position', 'name', 'balance', 'cards', 'bet']

    CREATE_QUERY = """
        CREATE TABLE players (
            table_id INT NOT NULL,
            position INT NOT NULL,
            name VARCHAR NOT NULL,
            balance INT NOT NULL,
            cards VARCHAR NOT NULL,
            bet int NOT NULL,
            PRIMARY KEY (table_id, position),
            UNIQUE (name)
        )
    """

    PLAYERS_RELATION_ROW = namedtuple('PlayersRelationRow', FIELDS)

    INSERT_QUERY = """
        INSERT INTO players ({})
        VALUES ({})
    """.format(','.join(FIELDS), ','.join(['?'] * len(FIELDS)))

    LOAD_BY_NAME_QUERY = """
        SELECT {}
        FROM players
        WHERE name = ?
    """.format(','.join(FIELDS))

    LOAD_ALL_QUERY = """
        SELECT {}
        FROM players
        ORDER BY table_id
    """.format(','.join(FIELDS))

    LOAD_BY_TABLE_ID_QUERY = """
        SELECT {}
        FROM players
        WHERE table_id = ?
    """.format(",".join(FIELDS))

    @classmethod
    async def load_all(cls):
        player_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_ALL_QUERY) as cursor:
            async for row in cursor:
                player_data.append(cls.PLAYERS_RELATION_ROW(*row)._asdict())
        return player_data

    @classmethod
    async def load_by_name(cls, name):
        row = await Database.instance().find_row(cls.LOAD_BY_NAME_QUERY, name)
        if row is not None:
            return cls.PLAYERS_RELATION_ROW(*row)._asdict()
        else:
            return None

    @classmethod
    async def load_by_table_id(cls, table_id):
        player_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_BY_TABLE_ID_QUERY, table_id) as cursor:
            async for row in cursor:
                player_data.append(cls.PLAYERS_RELATION_ROW(*row)._asdict())
        return player_data

    @classmethod
    async def add_player(cls, table_id, position, name, balance, cards, bet):  # pylint: disable=too-many-arguments
        db = Database.instance()
        await db.execute(cls.INSERT_QUERY, table_id, position, name, balance, cards, bet)
