import asyncio
import logging
from logging.config import dictConfig
import os
import sys
from argparse import ArgumentParser

from tornado.ioloop import IOLoop
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application

from pokerserver.configuration import LOGGING, ServerConfig
from pokerserver.controllers import HANDLERS, TablesController
from pokerserver.database import Database, TableConfig

LOG = logging.getLogger(__name__)


def make_app(args):
    return Application(
        HANDLERS,
        static_path='dist',
        autoreload=True,
        args=args
    )


async def setup(args):
    ServerConfig.set(timeout=args.timeout or None)
    await Database.connect(args.db)
    await TablesController.ensure_free_tables(args.free_tables, TableConfig(
        args.min_player_count, args.max_player_count, args.small_blind, args.big_blind, args.start_balance))


async def teardown():
    await Database.instance().close_connection()


def main():
    dictConfig(LOGGING)
    LOG = logging.getLogger(os.path.basename(sys.argv[0]))
    parser = ArgumentParser(
        description='Poker server for our Python workshop at TNG Technology Consulting.',
        epilog='And now let\'s try it out!'
    )
    parser.add_argument('--ip', default='127.0.0.1', type=str, help='IP address to bind to.')
    parser.add_argument('--port', default=5555, type=int, help='Port to liston on.')
    parser.add_argument('--free-tables', default=10, type=int, help='Number of tables that are kept ready in advance.')
    parser.add_argument('--db', default='poker.db', type=str, help='Path to SQLite database file.')
    parser.add_argument('--start-balance', default=40, type=int, help='The buy in for each client.')
    parser.add_argument('--min-player-count', default=4, type=int, help='Minimum number of players to start a game.')
    parser.add_argument('--max-player-count', default=8, type=int, help='Maximum number of players per table.')
    parser.add_argument('--small-blind', default=1, type=int, help='Small blind for every game.')
    parser.add_argument('--big-blind', default=2, type=int, help='Big blind for every game.')
    parser.add_argument('--timeout', default=0, type=float,
                        help='Interval during which a client has to send a reply in seconds. Use 0 to disable.')
    parser.add_argument('--turn-interval', default=2, type=float, help='Time each turn takes in seconds.')
    args = parser.parse_args()

    LOG.debug('Starting server...')
    AsyncIOMainLoop().install()
    asyncio.get_event_loop().run_until_complete(setup(args))
    app = make_app(args)
    LOG.debug('Listening on %s:%s...', args.ip, args.port)
    app.listen(address=args.ip, port=args.port)
    try:
        IOLoop.current().start()
    finally:
        asyncio.get_event_loop().run_until_complete(teardown())
    LOG.debug('Shut down.')


if __name__ == "__main__":
    main()
