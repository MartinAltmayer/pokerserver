from tornado.testing import gen_test

from pokerserver.models import Match, Player
from tests.utils import IntegrationTestCase, create_table


class TestFindBankruptPlayers(IntegrationTestCase):
    async def create_match(self, *balances):
        table_id = 1
        players = [
            Player(table_id, 1, 'a', balances[0], [], 0),
            Player(table_id, 2, 'b', balances[1], [], 0),
            Player(table_id, 3, 'c', balances[2], [], 0),
            Player(table_id, 4, 'd', balances[3], [], 0)
        ]

        table = await create_table(table_id=table_id, players=players, small_blind=10, big_blind=20)
        return Match(table)

    @gen_test
    async def test_bankrupt_players(self):
        match = await self.create_match(0, 20, 20, 0)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[0], players[3]], bankrupt_players)

    @gen_test
    async def test_small_blind_bankrupt(self):
        match = await self.create_match(20, 9, 20, 20)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[1]], bankrupt_players)

    @gen_test
    async def test_big_blind_bankrupt(self):
        match = await self.create_match(20, 10, 19, 20)
        players = match.table.players
        bankrupt_players = match.find_bankrupt_players(dealer=match.table.players[0])
        self.assertEqual([players[2]], bankrupt_players)

    @gen_test
    async def test_noone_bankrupt(self):
        match = await self.create_match(1, 10, 20, 1)
        self.assertEqual([], match.find_bankrupt_players(dealer=match.table.players[0]))
