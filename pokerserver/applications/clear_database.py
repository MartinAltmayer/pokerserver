import asyncio
from argparse import ArgumentParser

from pokerserver.database import Database, clear_relations


async def _clear_relations(db_path, exclude_uuids):
    db = await Database.connect(db_path)
    try:
        await clear_relations(exclude=['uuids'] if exclude_uuids else [])
    finally:
        await db.close_connection()


def main():
    parser = ArgumentParser(description='Clear all database tables')
    parser.add_argument(type=str, help='Path to SQLite database file.', dest='dbpath')
    parser.add_argument('-u', '--uuids', help='Exclude the uuids table', action='store_true')
    args = parser.parse_args()

    asyncio.get_event_loop().run_until_complete(_clear_relations(args.dbpath, args.uuids))


if __name__ == "__main__":
    main()
