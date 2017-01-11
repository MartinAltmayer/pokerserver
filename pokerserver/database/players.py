from collections import namedtuple

from pokerserver.database.database import convert_datetime
from .database import Database
from .relation import Relation
from .utils import make_card_list, from_card_list


class PlayersRelation(Relation):
    NAME = 'players'

    FIELDS = ['table_id', 'position', 'name', 'balance', 'cards', 'bet', 'last_seen', 'has_folded']

    CREATE_QUERY = """
        CREATE TABLE players (
            table_id INT NOT NULL,
            position INT NOT NULL,
            name VARCHAR NOT NULL,
            balance INT NOT NULL,
            cards VARCHAR NOT NULL,
            bet INT NOT NULL,
            last_seen TEXT NOT NULL,
            has_folded INT NOT NULL,
            PRIMARY KEY (table_id, position)
        )
    """

    DROP_QUERY = """
        DROP TABLE players
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
        WHERE name = ?
    """

    SET_BALANCE_AND_BET_QUERY = """
        UPDATE players
        SET balance = ?, bet = ?
        WHERE name = ?
    """

    SET_CARDS_QUERY = """
        UPDATE players
        SET cards = ?
        WHERE name = ?
    """

    SET_HAS_FOLDED_QUERY = """
        UPDATE players
        SET has_folded = ?
        WHERE name = ?
    """

    RESET_BETS_QUERY = """
        UPDATE players SET bet = 0 WHERE table_id = ?
    """

    RESET_BETS_AND_HAS_FOLDED_QUERY = """
        UPDATE players SET bet = 0, has_folded = 0 WHERE table_id = ?
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
        data['has_folded'] = bool(data['has_folded'])
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
                         last_seen, has_folded):
        assert position > 0
        cards = make_card_list(cards)
        await Database.instance().execute(cls.INSERT_QUERY, table_id, position, name, balance, cards, bet,
                                          last_seen, has_folded)

    @classmethod
    async def delete_player(cls, table_id, position):
        await Database.instance().execute(cls.DELETE_QUERY, table_id, position)

    @classmethod
    async def set_balance(cls, name, balance):
        await Database.instance().execute(cls.SET_BALANCE_QUERY, balance, name)

    @classmethod
    async def set_balance_and_bet(cls, name, balance, bet):
        assert balance is not None
        assert bet is not None
        await Database.instance().execute(cls.SET_BALANCE_AND_BET_QUERY, balance, bet, name)

    @classmethod
    async def set_cards(cls, name, cards):
        cards = make_card_list(cards)
        await Database.instance().execute(cls.SET_CARDS_QUERY, cards, name)

    @classmethod
    async def set_has_folded(cls, name, has_folded):
        await Database.instance().execute(cls.SET_HAS_FOLDED_QUERY, has_folded, name)

    @classmethod
    async def reset_bets(cls, table_id):
        await Database.instance().execute(cls.RESET_BETS_QUERY, table_id)

    @classmethod
    async def reset_bets_and_has_folded(cls, table_id):
        await Database.instance().execute(cls.RESET_BETS_AND_HAS_FOLDED_QUERY, table_id)
