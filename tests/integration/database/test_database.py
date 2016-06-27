from nose.tools import nottest
from tornado.testing import gen_test

from pokerserver.database import Database, RELATIONS, DbException
from pokerserver.database.database import DuplicateKeyError
from tests.integration.utils.integration_test import IntegrationTestCase


class TestDatabase(IntegrationTestCase):
    SETUP_DB_CONNECTION = False

    def check_connections_released(self):
        # pylint: disable=protected-access
        self.assertEqual(Database.POOL_SIZE, self.db._pool.freesize)

    async def check_table_exists(self, db, name):
        exists = await db.find_one("""
            SELECT 1
            FROM sqlite_master
            WHERE type="table" AND name="{}"
            """.format(name))
        return exists == 1

    @nottest
    async def create_test_table(self, db, row):
        await db.execute('CREATE TABLE test ( name VARCHAR, value INT )')
        await db.execute('INSERT INTO test (name, value) VALUES (?, ?)', *row)

    @gen_test
    async def test_connect(self):
        db = await self.connect_database()
        self.assertIsInstance(db, Database)

    @gen_test
    async def test_close(self):
        db = await self.connect_database()
        self.assertFalse(db.closed)
        await db.close()
        self.assertTrue(db.closed)

    @gen_test
    async def test_execute_with_statement(self):
        db = await self.connect_database()
        async with db.execute('SELECT 42') as cursor:
            row = await cursor.fetchone()
            self.assertEqual([42], list(row))
        self.assertTrue(cursor.closed)
        self.check_connections_released()

    @gen_test
    async def test_execute_direct(self):
        db = await self.connect_database()
        await db.execute("CREATE TABLE test ( an INT ) ")
        self.assertTrue(await self.check_table_exists(db, 'test'))

    @gen_test
    async def test_execute_with_params(self):
        db = await self.connect_database()
        async with db.execute('SELECT ?', 17) as cursor:
            row = await cursor.fetchone()
            self.assertEqual([17], list(row))

    @gen_test
    async def test_find_row(self):
        expected_row = ('player', 12)
        db = await self.connect_database()
        await self.create_test_table(db, expected_row)
        actual_row = await db.find_row('SELECT name, value FROM test')
        self.assertEqual(expected_row, actual_row)

    @gen_test
    async def test_find_row_returns_none(self):
        db = await self.connect_database()
        await self.create_test_table(db, ('otherPlayer', 12))
        row = await db.find_row('SELECT * FROM test WHERE name = "player"')
        self.assertIsNone(row)

    @gen_test
    async def test_find_one(self):
        db = await self.connect_database()
        value = await db.find_one('SELECT 42')
        self.assertEqual(42, value)
        self.check_connections_released()

    @gen_test
    async def test_find_one_returns_none(self):
        db = await self.connect_database()
        await self.create_test_table(db, ('otherPlayer', 12))
        self.assertIsNone(await db.find_one('SELECT * FROM test WHERE name = "player"'))

    @gen_test
    async def test_raise_exception(self):
        db = await self.connect_database()
        with self.assertRaises(DbException):
            await db.execute('STUPID QUERY')

    @gen_test
    async def test_create_tables(self):
        db = await self.connect_database()
        await db.create_tables()
        for table_class in RELATIONS:
            self.assertTrue(await self.check_table_exists(db, table_class.NAME))

    @gen_test
    async def test_insert_with_duplicate(self):
        db = await self.connect_database()
        await db.execute("""
            CREATE TABLE test (
                id INTEGER PRIMARY KEY,
                name UNIQUE
            )""")
        await db.execute("INSERT INTO test (id, name) VALUES (1, 'luke')")

        with self.assertRaises(DuplicateKeyError):
            await db.execute("INSERT INTO test (id, name) VALUES (1, 'leia')")

        with self.assertRaises(DuplicateKeyError):
            await db.execute("INSERT INTO test (id, name) VALUES (2, 'luke')")
