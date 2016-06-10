from tornado.web import RequestHandler

from pokerserver.version import NAME, DESCRIPTION, VERSION


class InfoController(RequestHandler):
    route = r'/info'

    async def get(self):
        self.write({
            'name': NAME,
            'description': DESCRIPTION,
            'version': VERSION
        })
