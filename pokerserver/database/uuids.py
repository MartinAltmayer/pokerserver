from uuid import UUID

from pokerserver.database import Database


class UUIDsRelation:
    NAME = 'tables'
    CREATE_QUERY = """
        CREATE TABLE uuids (
            uuid VARCHAR PRIMARY KEY,
            player_name VARCHAR NOT NULL
        )
    """

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
        await db.execute('INSERT INTO uuids (uuid, player_name) VALUES (?,?)', str(uuid), player_name)
