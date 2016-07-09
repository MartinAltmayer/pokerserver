from collections import namedtuple
from uuid import UUID

from .database import Database


class UUIDsRelation:
    NAME = 'tables'

    FIELDS = ['uuid', 'player_name']

    UUIDS_RELATION_ROW = namedtuple('UUIDsRelationRow', FIELDS)

    CREATE_QUERY = """
        CREATE TABLE uuids (
            uuid VARCHAR PRIMARY KEY,
            player_name VARCHAR NOT NULL UNIQUE
        )
    """

    LOAD_BY_UUID_QUERY = "SELECT uuid, player_name FROM uuids WHERE uuid = ?"

    INSERT_QUERY = "INSERT INTO uuids (uuid, player_name) VALUES (?,?)"

    @classmethod
    async def load_by_uuid(cls, uuid):
        data = await Database.instance().find_row(cls.LOAD_BY_UUID_QUERY, str(uuid))
        if data is not None:
            return cls.UUIDS_RELATION_ROW(*data)._asdict()
        else:
            return None

    @classmethod
    async def load_all(cls):
        player_name_by_uuid = {}
        db = Database.instance()
        async with db.execute("""
                SELECT uuid, player_name
                FROM uuids
                ORDER BY uuid
                """) as cursor:
            async for row in cursor:
                uuid_string, player_name = row
                player_name_by_uuid[UUID(uuid_string)] = player_name
        return player_name_by_uuid

    @classmethod
    async def add_uuid(cls, uuid, player_name):
        db = Database.instance()
        await db.execute(cls.INSERT_QUERY, str(uuid), player_name)
