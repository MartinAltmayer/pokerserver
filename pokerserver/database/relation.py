from .database import Database, DbException


class Relation:
    CREATE_QUERY = ""
    DROP_QUERY = ""
    CLEAR_QUERY = ""

    @classmethod
    async def create_relation(cls):
        await Database.instance().execute(cls.CREATE_QUERY)

    @classmethod
    async def drop_relation(cls):
        try:
            await Database.instance().execute(cls.DROP_QUERY)
        except DbException as exc:
            if not str(exc).startswith('no such table'):
                raise

    @classmethod
    async def clear_relation(cls):
        try:
            await Database.instance().execute(cls.CLEAR_QUERY)
        except DbException as exc:
            if not str(exc).startswith('no such table'):
                raise
