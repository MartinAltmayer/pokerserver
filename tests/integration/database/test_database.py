from datetime import datetime

from nose.tools import nottest
from tornado.testing import gen_test

from pokerserver.database import Database, DbException, DuplicateKeyError
from pokerserver.database.database import convert_datetime
from tests.utils import IntegrationTestCase


class TestDatabase(IntegrationTestCase):
    SETUP_DB_CONNECTION = False

    @nottest
    async def create_test_table(self, db, row):
        await db.execute('CREATE TABLE test ( name VARCHAR, value INT )')
        await db.execute('INSERT INTO test (name, value) VALUES (?, ?)', *row)

    @gen_test
    async def test_open_connection(self):
        db = await self.connect_database()
        self.assertIsInstance(db, Database)
        self.assertTrue(db.connected)

    @gen_test
    async def test_close_connection(self):
        db = await self.connect_database()
        self.assertFalse(db.closed)
        await db.close_connection()
        self.assertTrue(db.closed)

    @gen_test
    async def test_basic_query(self):
        db = await self.connect_database()
        result = await db.find_one("SELECT 42")
        self.assertEqual(42, result)

    @gen_test
    async def test_execute(self):
        db = await self.connect_database()
        await db.execute("CREATE TABLE test ( an INT ) ")
        self.assertTrue(await self.check_table_exists('test'))

    @gen_test
    async def test_execute_with_statement(self):
        db = await self.connect_database()
        async with db.execute('SELECT 42') as cursor:
            row = await cursor.fetchone()
            self.assertEqual([42], list(row))

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

    @gen_test
    async def test_fake_cursor(self):
        db = await self.connect_database()
        expected_rows = [('abc', 2), ('def', 3), ('ghi', 4)]
        await db.execute('CREATE TABLE test ( name VARCHAR, value INT )')
        for row in expected_rows:
            await db.execute('INSERT INTO test (name, value) VALUES (?, ?)', *row)

        actual_rows = []
        async with db.execute('SELECT name, value FROM test ORDER BY value') as cursor:
            async for row in cursor:
                actual_rows.append(row)

        self.assertEqual(expected_rows, actual_rows)

    @gen_test
    async def test_rowcount(self):
        db = await self.connect_database()
        await db.execute('CREATE TABLE test ( name VARCHAR, value INT )')
        async with db.execute('INSERT INTO test (name, value) VALUES (?, ?)', 'abc', 2) as cursor:
            self.assertEqual(1, cursor.rowcount)

    def test_convert_datetime(self):
        expected = datetime(2016, 7, 8, 21, 0, 30, 141000)
        self.assertEqual(expected, convert_datetime("2016-07-08 21:00:30.141"))
        expected = datetime(2016, 7, 8, 21, 0, 30)
        self.assertEqual(expected, convert_datetime("2016-07-08 21:00:30"))
