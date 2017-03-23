from tornado.web import RequestHandler

from pokerserver.version import NAME, DESCRIPTION, VERSION


class InfoController(RequestHandler):
    route = r'/info/?'

    async def get(self):
        """Endpoint for information about the server.
        ---
        description: Returns version information of the server.
        responses:
            200:
                description: Successful operation.
        """
        self.write({
            'name': NAME,
            'description': DESCRIPTION,
            'version': VERSION
        })
