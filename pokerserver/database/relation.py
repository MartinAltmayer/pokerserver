from .database import Database


class Relation:
    CREATE_QUERY = ""
    DROP_QUERY = ""
    CLEAR_QUERY = ""

    @classmethod
    async def create_relation(cls):
        await Database.instance().execute(cls.CREATE_QUERY)

    @classmethod
    async def drop_relation(cls):
        await Database.instance().execute(cls.DROP_QUERY)

    @classmethod
    async def clear_relation(cls):
        await Database.instance().execute(cls.CLEAR_QUERY)
