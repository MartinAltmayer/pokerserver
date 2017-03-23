from collections import namedtuple
from enum import Enum, unique

from .database import Database
from .relation import Relation
from .utils import from_card_list, from_pot_list_string, make_card_list, to_pot_list_string

TableConfig = namedtuple(
    'TableConfig', ['min_player_count', 'max_player_count', 'small_blind', 'big_blind', 'start_balance'])


@unique
class TableState(Enum):
    WAITING_FOR_PLAYERS = 'waiting for players'
    RUNNING_GAME = 'running game'
    CLOSED = 'closed'


class TablesRelation(Relation):
    NAME = 'tables'

    FIELDS = [
        'table_id',
        'name',
        'min_player_count',
        'max_player_count',
        'remaining_deck',
        'small_blind',
        'big_blind',
        'start_balance',
        'open_cards',
        'pots',
        'current_player',
        'current_player_token',
        'dealer',
        'state',
        'joined_players'
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
            start_balance INT NOT NULL,
            open_cards VARCHAR NOT NULL ,
            pots VARCHAR NOT NULL,
            current_player VARCHAR,
            current_player_token VARCHAR,
            dealer VARCHAR,
            state VARCHAR NOT NULL,
            joined_players VARCHAR
        )
    """

    DROP_IF_EXISTS_QUERY = """
        DROP TABLE IF EXISTS tables
    """

    CLEAR_QUERY = """
        DELETE FROM tables
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

    SET_DEALER_QUERY = """
        UPDATE tables
        SET dealer = ?
        WHERE table_id = ?
    """

    SET_CARDS_QUERY = """
        UPDATE tables
        SET remaining_deck=?, open_cards=?
        WHERE table_id = ?
    """

    SET_CURRENT_PLAYER_QUERY = """
        UPDATE tables
        SET current_player=?, current_player_token=?
        WHERE table_id = ?
    """

    GET_CURRENT_PLAYER_TOKEN_QUERY = """
        SELECT current_player_token FROM tables WHERE table_id=?
    """

    CHECK_CURRENT_PLAYER_QUERY = """
        UPDATE tables
        SET current_player=NULL, current_player_token=NULL
        WHERE table_id=? AND current_player=?
    """

    CHECK_CURRENT_PLAYER_AND_TOKEN_QUERY = """
        UPDATE tables
        SET current_player=NULL, current_player_token=NULL
        WHERE table_id=? AND current_player=? AND current_player_token=?
    """

    SET_POT_QUERY = """
        UPDATE tables SET pots = ? WHERE table_id = ?
    """

    ADD_JOINED_PLAYER_QUERY = """
        UPDATE tables SET joined_players = joined_players || ' ' || ? WHERE table_id = ?
    """

    SET_STATE_QUERY = """
        UPDATE tables SET state = ? WHERE table_id = ?
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
        return cls._from_db(row) if row is not None else None

    @classmethod
    async def load_table_by_name(cls, name):
        db = Database.instance()
        row = await db.find_row(cls.LOAD_BY_NAME_QUERY, name)
        return cls._from_db(row) if row is not None else None

    @classmethod
    def _from_db(cls, row):
        data = cls.TABLES_RELATION_ROW(*row)._asdict()
        data['config'] = TableConfig(
            data['min_player_count'],
            data['max_player_count'],
            data['small_blind'],
            data['big_blind'],
            data['start_balance']
        )
        for key in 'min_player_count', 'max_player_count', 'small_blind', 'big_blind', 'start_balance':
            del data[key]
        data['remaining_deck'] = from_card_list(data['remaining_deck'])
        data['open_cards'] = from_card_list(data['open_cards'])
        data['pots'] = from_pot_list_string(data['pots'])
        data['joined_players'] = data['joined_players'].split()
        data['state'] = TableState(data['state'])
        return data

    # pylint: disable=too-many-arguments, too-many-locals
    @classmethod
    async def create_table(cls, table_id, name, config, remaining_deck, open_cards, pots, current_player,
                           current_player_token, dealer, state, joined_players):
        db = Database.instance()
        remaining_deck = make_card_list(remaining_deck)
        open_cards = make_card_list(open_cards)
        pots = to_pot_list_string(pots)
        joined_players = ' '.join(joined_players or [])
        await db.execute(
            cls.INSERT_QUERY, table_id, name, config.min_player_count, config.max_player_count, remaining_deck,
            config.small_blind, config.big_blind, config.start_balance, open_cards, pots, current_player,
            current_player_token, dealer, state.value, joined_players
        )

    @classmethod
    async def set_dealer(cls, table_id, dealer):
        await Database.instance().execute(cls.SET_DEALER_QUERY, dealer, table_id)

    @classmethod
    async def set_current_player(cls, table_id, current_player, token):
        await Database.instance().execute(cls.SET_CURRENT_PLAYER_QUERY, current_player, token, table_id)

    @classmethod
    async def get_current_player_token(cls, table_id):
        return await Database.instance().find_one(cls.GET_CURRENT_PLAYER_TOKEN_QUERY, table_id)

    @classmethod
    async def set_cards(cls, table_id, remaining_deck, open_cards):
        remaining_deck = make_card_list(remaining_deck)
        open_cards = make_card_list(open_cards)
        await Database.instance().execute(
            cls.SET_CARDS_QUERY, remaining_deck, open_cards, table_id)

    @classmethod
    async def check_and_unset_current_player(cls, table_id, current_player, token=None):
        """In one atomic operation, check whether the given name (and optionally the token) coincides with
        the current player and if that is the case, set current_player and token to None.
        This is used to make sure that even the current player cannot play more than one turn.
        """
        db = Database.instance()
        if token is not None:
            context_manager = db.execute(
                cls.CHECK_CURRENT_PLAYER_AND_TOKEN_QUERY, table_id, current_player, token)
        else:
            context_manager = db.execute(cls.CHECK_CURRENT_PLAYER_QUERY, table_id, current_player)

        async with context_manager as cursor:
            return cursor.rowcount > 0

    @classmethod
    async def set_pots(cls, table_id, pot_dicts):
        await Database.instance().execute(cls.SET_POT_QUERY, to_pot_list_string(pot_dicts), table_id)

    @classmethod
    async def add_joined_player(cls, table_id, player_name):
        await Database.instance().execute(cls.ADD_JOINED_PLAYER_QUERY, player_name, table_id)

    @classmethod
    async def set_state(cls, table_id, state):
        await Database.instance().execute(cls.SET_STATE_QUERY, state.value, table_id)
