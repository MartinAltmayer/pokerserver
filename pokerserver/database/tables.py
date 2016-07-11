from collections import namedtuple

from .database import Database
from .utils import from_card_list, make_card_list, make_int_list, from_int_list

TableConfig = namedtuple('TableConfig', ['min_player_count', 'max_player_count', 'small_blind', 'big_blind'])


class TablesRelation:
    NAME = 'tables'

    FIELDS = [
        'table_id',
        'name',
        'min_player_count',
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
            min_player_count INT NOT NULL,
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

    LOAD_BY_ID_QUERY = """
        SELECT {}
        FROM tables
        WHERE table_id = ?
    """.format(','.join(FIELDS))

    LOAD_BY_NAME_QUERY = """
        SELECT {}
        FROM tables
        WHERE name = ?
    """.format(','.join(FIELDS))

    SET_SPECIAL_PLAYERS_QUERY = """
        UPDATE tables
        SET dealer=?, small_blind_player=?, big_blind_player=?, current_player=?
        WHERE table_id = ?
    """

    SET_CURRENT_PLAYER_QUERY = "UPDATE tables SET current_player=? WHERE table_id=?"

    SET_CARDS_QUERY = """
        UPDATE tables
        SET remaining_deck=?, open_cards=?
        WHERE table_id = ?
    """

    CHECK_CURRENT_PLAYER_QUERY = """
        UPDATE tables
        SET current_player=NULL
        WHERE table_id=? AND current_player=?
    """

    @classmethod
    async def load_all(cls):
        table_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_ALL_QUERY) as cursor:
            async for row in cursor:
                table_data.append(cls._from_db(row))
        return table_data

    @classmethod
    async def load_table_by_id(cls, table_id):
        db = Database.instance()
        row = await db.find_row(cls.LOAD_BY_ID_QUERY, table_id)
        if row is not None:
            return cls._from_db(row)
        else:
            return None

    @classmethod
    async def load_table_by_name(cls, name):
        db = Database.instance()
        row = await db.find_row(cls.LOAD_BY_NAME_QUERY, name)
        if row is not None:
            return cls._from_db(row)
        else:
            return None

    @classmethod
    def _from_db(cls, row):
        data = cls.TABLES_RELATION_ROW(*row)._asdict()
        data['config'] = TableConfig(
            data['min_player_count'], data['max_player_count'], data['small_blind'], data['big_blind'])
        for key in 'min_player_count', 'max_player_count', 'small_blind', 'big_blind':
            del data[key]
        data['remaining_deck'] = from_card_list(data['remaining_deck'])
        data['open_cards'] = from_card_list(data['open_cards'])
        data['side_pots'] = from_int_list(data['side_pots'])
        return data

    # pylint: disable=too-many-arguments, too-many-locals
    @classmethod
    async def create_table(cls, table_id, name, config, remaining_deck, open_cards, main_pot, side_pots,
                           current_player, dealer, small_blind_player, big_blind_player, is_closed):
        db = Database.instance()
        remaining_deck = make_card_list(remaining_deck)
        open_cards = make_card_list(open_cards)
        side_pots = make_int_list(side_pots)
        await db.execute(
            cls.INSERT_QUERY, table_id, name, config.min_player_count, config.max_player_count, remaining_deck,
            config.small_blind, config.big_blind, open_cards, main_pot, side_pots, current_player, dealer,
            small_blind_player, big_blind_player, is_closed
        )

    @classmethod
    async def set_special_players(cls, table_id, dealer, small_blind_player, big_blind_player, current_player):
        await Database.instance().execute(
            cls.SET_SPECIAL_PLAYERS_QUERY, dealer, small_blind_player, big_blind_player, current_player, table_id)

    @classmethod
    async def set_current_player(cls, table_id, current_player):
        await Database.instance().execute(cls.SET_CURRENT_PLAYER_QUERY, current_player, table_id)

    @classmethod
    async def set_cards(cls, table_id, remaining_deck, open_cards):
        remaining_deck = make_card_list(remaining_deck)
        open_cards = make_card_list(open_cards)
        await Database.instance().execute(
            cls.SET_CARDS_QUERY, remaining_deck, open_cards, table_id)

    @classmethod
    async def check_and_unset_current_player(cls, table_id, current_player):
        """In one atomic operation, check whether the given name coincides with the current player and if that is the
        case, set current_player to None. This is used to make sure that even the current player cannot play more
        than one turn.
        """
        db = Database.instance()
        async with db.execute(cls.CHECK_CURRENT_PLAYER_QUERY, table_id, current_player) as cursor:
            return cursor.rowcount > 0
