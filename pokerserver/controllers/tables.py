from tornado.web import RequestHandler

from pokerserver.models import Table


class TablesController(RequestHandler):
    route = r'/tables'

    async def get(self):
        tables = await Table.load_all()
        table_data = [table.to_dict_for_info() for table in tables]
        self.write({'tables': table_data})

    @classmethod
    async def ensure_free_tables(cls, number, max_player_count):
        tables = await Table.load_all()
        free_tables = len([table for table in tables if table.is_free()])
        if free_tables < number:
            await Table.create_tables(number - free_tables, max_player_count)
