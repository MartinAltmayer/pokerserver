from collections import namedtuple

from pokerserver.database import Database


class TablesRelation:
    NAME = 'tables'

    FIELDS = [
        'table_id',
        'name',
        'max_player_count',
        'remaining_deck',
        'small_blind',
        'big_blind',
        'open_cards',
        'main_pot',
        'side_pots',
        'current_player',
        'dealer',
        'small_blind_player',
        'big_blind_player',
        'is_closed'
    ]

    CREATE_QUERY = """
        CREATE TABLE tables (
            table_id INT PRIMARY KEY,
            name VARCHAR UNIQUE NOT NULL,
            max_player_count INT NOT NULL,
            remaining_deck VARCHAR NOT NULL,
            small_blind INT NOT NULL,
            big_blind INT NOT NULL,
            open_cards VARCHAR NOT NULL ,
            main_pot INT NOT NULL,
            side_pots VARCHAR NOT NULL,
            current_player VARCHAR,
            dealer VARCHAR,
            small_blind_player VARCHAR,
            big_blind_player VARCHAR,
            is_closed BOOLEAN NOT NULL
        )
    """

    TABLES_RELATION_ROW = namedtuple('TablesRelationRow', FIELDS)

    INSERT_QUERY = """
        INSERT INTO tables ({})
        VALUES ({})
    """.format(','.join(FIELDS), ','.join(['?'] * len(FIELDS)))

    LOAD_ALL_QUERY = """
        SELECT {}
        FROM tables
        ORDER BY table_id
    """.format(','.join(FIELDS))

    LOAD_BY_NAME_QUERY = """
        SELECT {}
        FROM tables
        WHERE name = ?
    """.format(','.join(FIELDS))

    @classmethod
    async def load_all(cls):
        table_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_ALL_QUERY) as cursor:
            async for row in cursor:
                table_data.append(cls.TABLES_RELATION_ROW(*row)._asdict())
        return table_data

    @classmethod
    async def load_table_by_name(cls, name):
        db = Database.instance()
        async with db.execute(cls.LOAD_BY_NAME_QUERY, name) as cursor:
            row = await cursor.fetchone()
            info_row = cls.TABLES_RELATION_ROW(*row)._asdict()
            return info_row

    # pylint: disable=too-many-arguments, too-many-locals
    @classmethod
    async def create_table(cls, table_id, name, max_player_count, remaining_deck, small_blind, big_blind, open_cards,
                           main_pot, side_pots, current_player, dealer, small_blind_player, big_blind_player,
                           is_closed):
        db = Database.instance()
        await db.execute(cls.INSERT_QUERY, table_id, name, max_player_count, remaining_deck, small_blind, big_blind,
                         open_cards, main_pot, side_pots, current_player, dealer, small_blind_player, big_blind_player,
                         is_closed)
