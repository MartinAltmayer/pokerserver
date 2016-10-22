import os
import asyncio
from asyncio.futures import Future
import tempfile
from unittest.mock import Mock

from tornado.platform.asyncio import AsyncIOLoop
from tornado.testing import AsyncTestCase, AsyncHTTPTestCase
from tornado.web import Application

from pokerserver.controllers import HANDLERS
from pokerserver.database import Database, PlayersRelation, TablesRelation, TableConfig
from pokerserver.models.table import Table


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
        if self.SETUP_DB_CONNECTION:
            self.db = self.get_asyncio_loop().run_until_complete(self.connect_database())
            self.get_asyncio_loop().run_until_complete(self.db.create_tables())

    def tearDown(self):
        if self.db is not None:
            self.get_asyncio_loop().run_until_complete(self.db.close())
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


class IntegrationHttpTestCase(IntegrationTestCase, AsyncHTTPTestCase):
    def setUp(self):
        self.args = Mock()
        super().setUp()

    def get_app(self):
        return Application(HANDLERS, args=self.args)

    async def fetch_async(self, path, **kwargs):
        result = await self.http_client.fetch(self.get_url(path), **kwargs)
        return result


def return_done_future(result=None, exception=None):
    def future_creator(*args, **kwargs):  # pylint: disable=unused-argument
        future = Future()
        if exception is not None:
            future.set_exception(exception)
        else:
            future.set_result(result)
        return future

    return future_creator


async def create_table(table_id=1, name='Table', min_player_count=2, max_player_count=10, small_blind=1,
                       big_blind=2, start_balance=10,
                       remaining_deck=None, open_cards=None, main_pot=0, side_pots=None,
                       current_player=None, current_player_token=None, dealer=None,
                       is_closed=False, joined_players=None, players=None):
    # pylint: disable=too-many-locals, too-many-arguments
    remaining_deck = remaining_deck or []
    open_cards = open_cards or []
    side_pots = side_pots or []
    config = TableConfig(min_player_count, max_player_count, small_blind, big_blind, start_balance)
    await TablesRelation.create_table(
        table_id=table_id,
        name=name,
        config=config,
        remaining_deck=remaining_deck,
        open_cards=open_cards,
        main_pot=main_pot,
        side_pots=side_pots,
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
            player.has_folded
        )
    return await Table.load_by_name(name)
