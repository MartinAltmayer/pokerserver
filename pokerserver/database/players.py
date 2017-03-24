from collections import namedtuple
from enum import Enum, unique

from .database import Database, convert_datetime
from .relation import Relation
from .utils import from_card_list, make_card_list


class PlayersRelation(Relation):
    NAME = 'players'

    FIELDS = ['table_id', 'position', 'name', 'balance', 'cards', 'bet', 'last_seen', 'state']

    CREATE_QUERY = """
        CREATE TABLE players (
            table_id INT NOT NULL,
            position INT NOT NULL,
            name VARCHAR NOT NULL,
            balance INT NOT NULL,
            cards VARCHAR NOT NULL,
            bet INT NOT NULL,
            last_seen TEXT NOT NULL,
            state VARCHAR NOT NULL,
            PRIMARY KEY (table_id, position),
            UNIQUE (table_id, name)
        )
    """

    DROP_IF_EXISTS_QUERY = """
        DROP TABLE IF EXISTS players
    """

    CLEAR_QUERY = """
        DELETE FROM players
    """

    PLAYERS_RELATION_ROW = namedtuple('PlayersRelationRow', FIELDS)

    INSERT_QUERY = """
        INSERT INTO players ({})
        VALUES ({})
    """.format(','.join(FIELDS), ','.join(['?'] * len(FIELDS)))

    DELETE_QUERY = """
        DELETE FROM players WHERE table_id = ? AND position = ?
    """

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

    LOAD_BY_POSITION_QUERY = """
        SELECT {}
        FROM players
        WHERE table_id = ? AND position = ?
    """.format(','.join(FIELDS))

    LOAD_BY_TABLE_ID_QUERY = """
        SELECT {}
        FROM players
        WHERE table_id = ?
    """.format(",".join(FIELDS))

    SET_BALANCE_QUERY = """
        UPDATE players
        SET balance = ?
        WHERE name = ? AND table_id = ?
    """

    SET_BET_QUERY = """
        UPDATE players
        SET bet = ?
        WHERE name = ? AND table_id = ?
    """

    SET_BALANCE_AND_BET_QUERY = """
        UPDATE players
        SET balance = ?, bet = ?
        WHERE name = ? AND table_id = ?
    """

    SET_CARDS_QUERY = """
        UPDATE players
        SET cards = ?
        WHERE name = ? AND table_id = ?
    """

    SET_STATE_QUERY = """
        UPDATE players
        SET state = ?
        WHERE name = ? AND table_id = ?
    """

    @classmethod
    async def load_all(cls):
        player_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_ALL_QUERY) as cursor:
            async for row in cursor:
                player_data.append(cls._from_db(row))
        return player_data

    @classmethod
    def _from_db(cls, row):
        data = cls.PLAYERS_RELATION_ROW(*row)._asdict()
        data['cards'] = from_card_list(data['cards'])
        data['last_seen'] = convert_datetime(data['last_seen'])
        data['state'] = PlayerState(data['state'])
        return data

    @classmethod
    async def load_by_name(cls, name):
        row = await Database.instance().find_row(cls.LOAD_BY_NAME_QUERY, name)
        return cls._from_db(row) if row is not None else None

    @classmethod
    async def load_by_table_id(cls, table_id):
        player_data = []
        db = Database.instance()
        async with db.execute(cls.LOAD_BY_TABLE_ID_QUERY, table_id) as cursor:
            async for row in cursor:
                player_data.append(cls._from_db(row))
        return player_data

    @classmethod
    async def load_by_position(cls, table_id, position):
        row = await Database.instance().find_row(cls.LOAD_BY_POSITION_QUERY, table_id, position)
        return cls._from_db(row) if row is not None else None

    @classmethod
    async def add_player(cls, table_id, position, name, balance, cards, bet,  # pylint: disable=too-many-arguments
                         last_seen, state):
        assert position > 0
        cards = make_card_list(cards)
        await Database.instance().execute(cls.INSERT_QUERY, table_id, position, name, balance, cards, bet,
                                          last_seen, state.value)

    @classmethod
    async def delete_player(cls, table_id, position):
        await Database.instance().execute(cls.DELETE_QUERY, table_id, position)

    @classmethod
    async def set_balance(cls, name, table_id, balance):
        await Database.instance().execute(cls.SET_BALANCE_QUERY, balance, name, table_id)

    @classmethod
    async def set_bet(cls, name, table_id, bet):
        await Database.instance().execute(cls.SET_BET_QUERY, bet, name, table_id)

    @classmethod
    async def set_balance_and_bet(cls, name, table_id, balance, bet):
        assert balance is not None
        assert bet is not None
        await Database.instance().execute(cls.SET_BALANCE_AND_BET_QUERY, balance, bet, name, table_id)

    @classmethod
    async def set_cards(cls, name, table_id, cards):
        cards = make_card_list(cards)
        await Database.instance().execute(cls.SET_CARDS_QUERY, cards, name, table_id)

    @classmethod
    async def set_state(cls, name, table_id, state):
        await Database.instance().execute(cls.SET_STATE_QUERY, state.value, name, table_id)


@unique
class PlayerState(Enum):
    PLAYING = 'playing'
    FOLDED = 'folded'
    ALL_IN = 'all in'
    SITTING_OUT = 'sitting out'
