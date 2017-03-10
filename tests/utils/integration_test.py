import asyncio
import json
import os
import tempfile
from unittest.mock import Mock

from tornado.platform.asyncio import AsyncIOLoop
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase
from tornado.web import Application

from pokerserver.configuration import ServerConfig
from pokerserver.controllers import HANDLERS
from pokerserver.database import create_relations, Database, PlayersRelation, TablesRelation, TableConfig
from pokerserver.models import Table, Pot


class IntegrationTestCase(AsyncTestCase):
    SETUP_DB_CONNECTION = True
    db = None
    _db_path = None

    @classmethod
    def setUpClass(cls):
        # It would be simpler and faster to use an in-memory database.
        # However, I couldn't figure out how to do this with aioodbc.
        _, cls._db_path = tempfile.mkstemp()

    @classmethod
    def tearDownClass(cls):
        if cls._db_path is not None and os.path.exists(cls._db_path):
            os.remove(cls._db_path)

    def setUp(self):
        self._tornado_loop = None
        super().setUp()
        ServerConfig.clear()
        if self.SETUP_DB_CONNECTION:
            self.db = self.get_asyncio_loop().run_until_complete(self.connect_database())
            self.get_asyncio_loop().run_until_complete(create_relations())

    def tearDown(self):
        if self.db is not None:
            self.get_asyncio_loop().run_until_complete(self.db.close_connection())
            self.db = None
            os.truncate(self._db_path, 0)
        super().tearDown()

    def get_new_ioloop(self):
        assert self._tornado_loop is None, 'get_new_ioloop must not be called twice in one test case'
        self._tornado_loop = AsyncIOLoop()
        asyncio.set_event_loop(self._tornado_loop.asyncio_loop)
        return self._tornado_loop

    def get_asyncio_loop(self):
        return self._tornado_loop.asyncio_loop

    async def connect_database(self):
        self.db = await Database.connect(self._db_path, loop=self.get_asyncio_loop())
        return self.db

    @staticmethod
    async def check_relation_exists(name):
        db = Database.instance()
        exists = await db.find_one("""
            SELECT 1
            FROM sqlite_master
            WHERE type="table" AND name=?
            """, name)
        return exists == 1


class IntegrationHttpTestCase(IntegrationTestCase, AsyncHTTPTestCase):
    def setUp(self):
        self.args = Mock(turn_delay=None)
        super().setUp()

    def get_app(self):
        return Application(HANDLERS, args=self.args)

    async def fetch_async(self, path, **kwargs):
        result = await self.http_client.fetch(self.get_url(path), **kwargs)
        return result

    async def post_with_uuid(self, url, uuid, body=None, **kwargs):
        separator = '&' if '?' in url else '?'
        return await self.post('{}{}uuid={}'.format(url, separator, uuid), body=body, **kwargs)

    async def post(self, url, body=None, **kwargs):
        body = json.dumps(body or {})
        return await self.fetch_async(url, body=body, method='POST', **kwargs)


async def create_table(table_id=1, name='Table', min_player_count=2, max_player_count=10, small_blind=1, big_blind=2,
                       start_balance=10, remaining_deck=None, open_cards=None, pots=None, current_player=None,
                       current_player_token=None, dealer=None, is_closed=False, joined_players=None, players=None):
    # pylint: disable=too-many-locals, too-many-arguments
    remaining_deck = remaining_deck or []
    open_cards = open_cards or []
    config = TableConfig(min_player_count, max_player_count, small_blind, big_blind, start_balance)
    await TablesRelation.create_table(
        table_id=table_id,
        name=name,
        config=config,
        remaining_deck=remaining_deck,
        open_cards=open_cards,
        pots=pots or [Pot().to_dict()],
        current_player=current_player,
        current_player_token=current_player_token,
        dealer=dealer,
        is_closed=is_closed,
        joined_players=joined_players
    )
    for player in players or []:
        await PlayersRelation.add_player(
            player.table_id,
            player.position,
            player.name,
            player.balance,
            player.cards,
            player.bet,
            player.last_seen,
            player.state
        )
    return await Table.load_by_name(name)
