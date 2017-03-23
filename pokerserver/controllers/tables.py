from tornado.web import RequestHandler

from pokerserver.models import Table


class TablesController(RequestHandler):
    route = r'/tables/?'

    async def get(self):
        """Endpoint to list all tables.
        ---
        description: Returns an array of table infos.
        responses:
            200:
                description: Successful operation.
        """
        tables = await Table.load_all()
        table_data = [table.to_dict_for_info() for table in tables]
        self.write({'tables': table_data})
