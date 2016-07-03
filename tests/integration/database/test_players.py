from tornado.testing import gen_test

from pokerserver.database import PlayersRelation
from pokerserver.database.utils import from_card_list
from tests.integration.utils.integration_test import IntegrationTestCase


class TestPlayersRelation(IntegrationTestCase):
    PLAYER_ROWS = [
        (1, 1, 'player1', 10, 'cards1', 5),
        (1, 2, 'player2', 20, 'cards2', 10),
        (2, 3, 'player3', 30, 'cards3', 15)
    ]
    PLAYER_DATA = [{
        'table_id': table_id,
        'position': position,
        'name': name,
        'balance': balance,
        'cards': from_card_list(cards),
        'bet': bet
    } for table_id, position, name, balance, cards, bet in PLAYER_ROWS]

    async def create_players(self):
        for fields in self.PLAYER_ROWS:
            await self.db.execute(PlayersRelation.INSERT_QUERY, *fields)

    @gen_test
    async def test_load_all(self):
        await self.create_players()
        players = await PlayersRelation.load_all()
        self.assertCountEqual(self.PLAYER_DATA, players)

    @gen_test
    async def test_load_by_name(self):
        await self.create_players()
        player = await PlayersRelation.load_by_name('player1')
        self.assertEqual(self.PLAYER_DATA[0], player)

    @gen_test
    async def test_load_by_name_not_found(self):
        await self.create_players()
        player = await PlayersRelation.load_by_name('idonotexist')
        self.assertIsNone(player)

    @gen_test
    async def test_load_by_table_id(self):
        await self.create_players()
        players = await PlayersRelation.load_by_table_id(1)
        self.assertCountEqual(self.PLAYER_DATA[:2], players)

    @gen_test
    async def test_add_player(self):
        await PlayersRelation.add_player(**self.PLAYER_DATA[0])
        player = await PlayersRelation.load_by_name('player1')
        self.assertEqual(self.PLAYER_DATA[0], player)

    @gen_test
    async def test_set_balance(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        new_balance = player_data['balance'] + 100
        await PlayersRelation.set_balance(player_data['name'], new_balance)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_balance, player['balance'])

    @gen_test
    async def test_set_cards(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        cards = ['As', '2h']
        assert cards != player_data['cards']
        await PlayersRelation.set_cards(player_data['name'], cards)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(cards, player['cards'])
