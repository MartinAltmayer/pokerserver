from tornado.web import RequestHandler

from pokerserver.models import Table


class TableController(RequestHandler):
    route = r'/table/([^/]+)'

    async def get(self, name):  # pylint: disable=arguments-differ
        player = None
        table = await Table.load_by_name(name)
        self.write(table.to_dict(player))
