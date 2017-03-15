from argparse import ArgumentParser
from asyncio import get_event_loop, sleep
import logging
from logging.config import dictConfig
import os
from os.path import abspath, dirname, join
import sys

from tornado.ioloop import IOLoop
from tornado.platform.asyncio import AsyncIOMainLoop
from tornado.web import Application

import pokerserver
from pokerserver.configuration import LOGGING, ServerConfig
from pokerserver.controllers import HANDLERS
from pokerserver.database import Database, TableConfig
from pokerserver.models import Table

LOG = logging.getLogger(__name__)

ENSURE_TABLES_INTERVAL_SECONDS = 10


def make_app(args):
    static_path = join(dirname(abspath(pokerserver.__file__)), 'static')
    return Application(
        HANDLERS,
        static_path=static_path,
        autoreload=True,
        args=args
    )


async def setup(args):
    ServerConfig.set(timeout=args.timeout or None)
    await Database.connect(args.db)


async def ensure_free_tables(args):
    while True:
        try:
            LOG.info('Calling Table.ensure_free_tables to ensure %s tables are available...', args.free_tables)
            number_of_created_tables = await Table.ensure_free_tables(
                args.free_tables,
                TableConfig(
                    args.min_player_count,
                    args.max_player_count,
                    args.small_blind,
                    args.big_blind,
                    args.start_balance
                )
            )
            LOG.info('Created %s tables.', number_of_created_tables)
            await sleep(ENSURE_TABLES_INTERVAL_SECONDS)
        except Exception:  # pylint: disable=broad-except
            LOG.exception('An error occurred in ensure_free_tables!')


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
    parser.add_argument('--turn-delay', default=None, type=float,
                        help='Waiting time before the next player becomes active in seconds.')
    parser.add_argument('--timeout', default=0, type=float,
                        help='Interval during which a client has to send a reply in seconds. Use 0 to disable.')
    parser.add_argument('--password', default='', type=str, help='Password to protect the frontend.')
    parser.add_argument('--showdown-timeout', default=None, type=float,
                        help='Waiting time in seconds before the next hand starts after a showdown.')
    args = parser.parse_args()

    LOG.debug('Starting server...')
    AsyncIOMainLoop().install()
    get_event_loop().run_until_complete(setup(args))
    get_event_loop().create_task(ensure_free_tables(args))
    app = make_app(args)
    LOG.debug('Listening on %s:%s...', args.ip, args.port)
    app.listen(address=args.ip, port=args.port)
    try:
        IOLoop.current().start()
    finally:
        get_event_loop().run_until_complete(teardown())
    LOG.debug('Shut down.')


if __name__ == "__main__":
    main()
