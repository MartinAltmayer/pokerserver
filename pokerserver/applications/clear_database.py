import asyncio
from argparse import ArgumentParser

from pokerserver.database import Database


async def clear_tables(db_path, exclude_uuids):
    db = await Database.connect(db_path)
    try:
        await db.clear_tables(exclude=['uuids'] if exclude_uuids else [])
    finally:
        await db.close()


def main():
    parser = ArgumentParser(description='Clear all database tables')
    parser.add_argument(type=str, help='Path to SQLite database file.', dest='db')
    parser.add_argument('-u', '--uuids', help='Exclude the uuids table', action='store_true')
    args = parser.parse_args()

    asyncio.get_event_loop().run_until_complete(clear_tables(args.db, args.uuids))


if __name__ == "__main__":
    main()
