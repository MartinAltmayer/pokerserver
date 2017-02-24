from nose.tools import assert_raises
from tornado.testing import gen_test

from pokerserver.database import (create_relations, clear_relations, RELATIONS, Database, PlayersRelation,
                                  TablesRelation, UUIDsRelation, DbException)
from tests.utils import IntegrationTestCase


class TestRelations(IntegrationTestCase):
    @gen_test
    async def test_create_relations(self):
        await create_relations()
        for table_class in RELATIONS:
            self.assertTrue(await self.check_relation_exists(table_class.NAME))

    @gen_test
    async def test_create_relations_multiple_times(self):
        for _ in range(100):
            await create_relations()
        for table_class in RELATIONS:
            self.assertTrue(await self.check_relation_exists(table_class.NAME))

    @gen_test
    async def test_clear_relations(self):
        await create_relations()

        db = Database.instance()
        await db.execute(PlayersRelation.INSERT_QUERY, *([1] * len(PlayersRelation.FIELDS)))
        await db.execute(TablesRelation.INSERT_QUERY, *([1] * len(TablesRelation.FIELDS)))
        await db.execute(UUIDsRelation.INSERT_QUERY, *([1] * len(UUIDsRelation.FIELDS)))

        await clear_relations(exclude=['uuids'])

        self.assertEqual(0, await db.find_one('SELECT COUNT(*) FROM players'))
        self.assertEqual(0, await db.find_one('SELECT COUNT(*) FROM tables'))
        self.assertEqual(1, await db.find_one('SELECT COUNT(*) FROM uuids'))

    @gen_test
    async def test_clear_relations_with_missing_relation(self):
        await create_relations()

        db = Database.instance()
        await db.execute(TablesRelation.INSERT_QUERY, *([1] * len(TablesRelation.FIELDS)))
        await db.execute(UUIDsRelation.INSERT_QUERY, *([1] * len(UUIDsRelation.FIELDS)))
        await PlayersRelation.drop_relation()

        with assert_raises(DbException):
            await clear_relations(exclude=['uuids'])
