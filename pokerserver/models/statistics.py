from pokerserver.database import StatisticsRelation


class Statistics:
    def __init__(self, player_statistics):
        self.player_statistics = player_statistics

    @classmethod
    async def load(cls):
        statistics = await StatisticsRelation.load_all()
        return cls([PlayerStatistics(**player_statistics) for player_statistics in statistics])

    def to_dict(self):
        return {
            statistics.player_name: statistics.to_dict() for statistics in self.player_statistics
        }

    @classmethod
    async def init_statistics(cls, player_name):
        StatisticsRelation.init_statistics(player_name)

    @classmethod
    async def increment_statistics(cls, player_name, matches, buy_in, gain):
        await StatisticsRelation.increment_statistics(player_name, matches, buy_in, gain)


class PlayerStatistics:
    def __init__(self, player_name, matches, buy_in, gain):
        self.player_name = player_name
        self.matches = matches
        self.buy_in = buy_in
        self.gain = gain

    def to_dict(self):
        return {
            'matches': self.matches,
            'buy_in': self.buy_in,
            'gain': self.gain
        }
