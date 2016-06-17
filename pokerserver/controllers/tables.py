from tornado.web import RequestHandler

from pokerserver.models.table import Table


class TablesController(RequestHandler):
    route = r'/tables'

    async def get(self):
        tables = await Table.load_all()
        table_data = [table.to_dict() for table in tables]
        self.write({'tables': table_data})
