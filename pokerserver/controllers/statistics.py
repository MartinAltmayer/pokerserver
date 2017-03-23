from tornado.web import RequestHandler

from pokerserver.models import Statistics


class StatisticsController(RequestHandler):
    route = r'/statistics/?'

    async def get(self):
        """Statistics endpoint
        ---
        description: returns player statistics
        responses:
            200:
                description: list of all accumulated player statistics
        """
        statistics = await Statistics.load()
        self.write(statistics.to_dict())
