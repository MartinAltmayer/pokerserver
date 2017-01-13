import asyncio
from argparse import ArgumentParser

from pokerserver.database import Database, create_relations


async def _create_relations(db_path):
    db = await Database.connect(db_path)
    try:
        await create_relations()
    finally:
        await db.close_connection()


def main():
    parser = ArgumentParser(description='Create necessary database tables')
    parser.add_argument(type=str, default='poker.db', help='Path to SQLite database file.', dest='dbpath')
    args = parser.parse_args()
    asyncio.get_event_loop().run_until_complete(_create_relations(args.dbpath))


if __name__ == "__main__":
    main()
