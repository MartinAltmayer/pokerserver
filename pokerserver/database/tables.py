from collections import namedtuple

from .database import Database
from .utils import from_card_list, make_card_list, make_int_list, from_int_list

TableConfig = namedtuple(
    'TableConfig', ['min_player_count', 'max_player_count', 'small_blind', 'big_blind', 'start_balance'])


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
        'start_balance',
        'open_cards',
        'main_pot',
        'side_pots',
        'current_player',
        'current_player_token',
        'dealer',
        'small_blind_player',
        'big_blind_player',
        'highest_bet_player',
        'is_closed',
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
            main_pot INT NOT NULL,
            side_pots VARCHAR NOT NULL,
            current_player VARCHAR,
            current_player_token VARCHAR,
            dealer VARCHAR,
            small_blind_player VARCHAR,
            big_blind_player VARCHAR,
            highest_bet_player VARCHAR,
            is_closed BOOLEAN NOT NULL,
            joined_players VARCHAR
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
        SET {}
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
        UPDATE tables SET main_pot = ? WHERE table_id = ?
    """

    ADD_JOINED_PLAYER_QUERY = """
        UPDATE tables SET joined_players = joined_players || ' ' || ? WHERE table_id = ?
    """

    CLOSE_TABLE_QUERY = """
        UPDATE tables SET is_closed = 1 WHERE table_id = ?
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
        data['side_pots'] = from_int_list(data['side_pots'])
        data['joined_players'] = data['joined_players'].split()
        return data

    # pylint: disable=too-many-arguments, too-many-locals
    @classmethod
    async def create_table(cls, table_id, name, config, remaining_deck, open_cards, main_pot, side_pots,
                           current_player, current_player_token, dealer, small_blind_player,
                           big_blind_player, highest_bet_player, is_closed, joined_players):
        db = Database.instance()
        remaining_deck = make_card_list(remaining_deck)
        open_cards = make_card_list(open_cards)
        side_pots = make_int_list(side_pots)
        joined_players = ' '.join(joined_players or [])
        await db.execute(
            cls.INSERT_QUERY, table_id, name, config.min_player_count, config.max_player_count, remaining_deck,
            config.small_blind, config.big_blind, config.start_balance, open_cards, main_pot, side_pots,
            current_player, current_player_token, dealer, small_blind_player, big_blind_player,
            highest_bet_player, is_closed, joined_players
        )

    @classmethod
    async def set_special_players(cls, table_id, **kwargs):
        assert set(kwargs.keys()) <= {
            'dealer', 'small_blind_player', 'big_blind_player', 'highest_bet_player'}
        if len(kwargs) == 0:
            return
        set_clause = ', '.join('{}=?'.format(key) for key in kwargs)
        params = list(kwargs.values()) + [table_id]
        await Database.instance().execute(cls.SET_SPECIAL_PLAYERS_QUERY.format(set_clause), *params)

    @classmethod
    async def set_current_player(cls, table_id, current_player, token):
        await Database.instance().execute(cls.SET_CURRENT_PLAYER_QUERY, current_player, token, table_id)

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
    async def set_pot(cls, table_id, amount):
        await Database.instance().execute(cls.SET_POT_QUERY, amount, table_id)

    @classmethod
    async def add_joined_player(cls, table_id, player_name):
        await Database.instance().execute(cls.ADD_JOINED_PLAYER_QUERY, player_name, table_id)

    @classmethod
    async def close_table(cls, table_id):
        await Database.instance().execute(cls.CLOSE_TABLE_QUERY, table_id)
