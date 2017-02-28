from tornado.web import RequestHandler

from pokerserver.models import Statistics


class StatisticsController(RequestHandler):
    route = r'/statistics'

    async def get(self):
        statistics = await Statistics.load()
        self.write(statistics.to_dict())
