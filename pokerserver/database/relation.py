from .database import Database, DbException


class Relation:
    MAXIMUM_TRIES = 10

    NAME = ''

    CREATE_QUERY = ''
    DROP_IF_EXISTS_QUERY = ''
    CLEAR_QUERY = ''

    EXISTS_QUERY = """
        SELECT 1
        FROM sqlite_master
        WHERE type="table" AND name=?
    """

    @classmethod
    async def create_relation(cls):
        # Retry creating relation as sometimes seems DROP TABLE seems to become effective with some delay.
        for _ in range(cls.MAXIMUM_TRIES):
            try:
                await Database.instance().execute(cls.CREATE_QUERY)
                return
            except DbException as exc:
                if 'already exists' not in str(exc):
                    raise
        raise DbException('Could not create relation after {} tries.'.format(cls.MAXIMUM_TRIES))

    @classmethod
    async def drop_relation(cls):
        await Database.instance().execute(cls.DROP_IF_EXISTS_QUERY)

    @classmethod
    async def clear_relation(cls):
        await Database.instance().execute(cls.CLEAR_QUERY)

    @classmethod
    async def relation_exists(cls):
        exists = await Database.instance().find_one(cls.EXISTS_QUERY, cls.NAME)
        return exists == 1
