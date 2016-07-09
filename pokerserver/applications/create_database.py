import asyncio
from argparse import ArgumentParser

from pokerserver.database import Database


async def create_tables(db_path):
    db = await Database.connect(db_path)
    try:
        await db.create_tables()
    finally:
        await db.close()


def main():
    parser = ArgumentParser(description='Create necessary database tables')
    parser.add_argument(type=str, default='poker.db', help='Path to SQLite database file.', dest='db')
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(create_tables(args.db))


if __name__ == "__main__":
    main()
