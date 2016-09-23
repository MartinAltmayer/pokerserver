from datetime import datetime
from tornado.testing import gen_test

from pokerserver.database import PlayersRelation
from pokerserver.database.utils import from_card_list
from tests.integration.utils.integration_test import IntegrationTestCase


class TestPlayersRelation(IntegrationTestCase):
    PLAYER_ROWS = [
        (1, 1, 'player1', 10, 'cards1', 5, datetime.fromtimestamp(123), False),
        (1, 2, 'player2', 20, 'cards2', 10, datetime.fromtimestamp(123), False),
        (2, 3, 'player3', 20, 'cards3', 10, datetime.fromtimestamp(123), False),
        (2, 4, 'player4', 30, 'cards3', 0, datetime.fromtimestamp(123), True)
    ]
    PLAYER_DATA = [{
        'table_id': table_id,
        'position': position,
        'name': name,
        'balance': balance,
        'cards': from_card_list(cards),
        'bet': bet,
        'last_seen': last_seen,
        'has_folded': has_folded
    } for table_id, position, name, balance, cards, bet, last_seen, has_folded in PLAYER_ROWS]

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
    async def test_load_by_position(self):
        await self.create_players()
        player = await PlayersRelation.load_by_position(2, 3)
        self.assertEqual(self.PLAYER_DATA[2], player)

    @gen_test
    async def test_load_by_position_not_found(self):
        await self.create_players()
        player = await PlayersRelation.load_by_position(1, 3)
        self.assertIsNone(player)

    @gen_test
    async def test_add_player(self):
        await PlayersRelation.add_player(**self.PLAYER_DATA[0])
        player = await PlayersRelation.load_by_name('player1')
        self.assertEqual(self.PLAYER_DATA[0], player)

    @gen_test
    async def test_delete_player(self):
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        self.assertIsNotNone(await PlayersRelation.load_by_name(player_data['name']))
        await PlayersRelation.delete_player(player_data['table_id'], player_data['position'])
        self.assertIsNone(await PlayersRelation.load_by_name(player_data['name']))

    @gen_test
    async def test_set_balance(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        new_balance = player_data['balance'] + 100
        await PlayersRelation.set_balance(player_data['name'], new_balance)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_balance, player['balance'])

    @gen_test
    async def test_set_balance_and_bet(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        new_balance = player_data['balance'] + 100
        new_bet = player_data['bet'] + 20
        await PlayersRelation.set_balance_and_bet(player_data['name'], new_balance, new_bet)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_balance, player['balance'])
        self.assertEqual(new_bet, player['bet'])

    @gen_test
    async def test_set_cards(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        cards = ['As', '2h']
        assert cards != player_data['cards']
        await PlayersRelation.set_cards(player_data['name'], cards)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(cards, player['cards'])

    @gen_test
    async def test_set_has_folded(self):
        await PlayersRelation.add_player(*self.PLAYER_ROWS[0])
        player_data = self.PLAYER_DATA[0]
        assert not player_data['has_folded']

        await PlayersRelation.set_has_folded(player_data['name'], True)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertTrue(player['has_folded'])

    @gen_test
    async def test_reset_bets(self):
        assert any(data['bet'] != 0 and data['table_id'] == 1 for data in self.PLAYER_DATA)
        await self.create_players()
        await PlayersRelation.reset_bets(1)

        players = await PlayersRelation.load_by_table_id(1)
        for player in players:
            self.assertEqual(0, player['bet'])

    @gen_test
    async def test_reset_bets_and_has_folded(self):
        assert any(data['bet'] != 0 and data['table_id'] == 2 for data in self.PLAYER_DATA)
        assert any(data['has_folded'] and data['table_id'] == 2 for data in self.PLAYER_DATA)
        await self.create_players()
        await PlayersRelation.reset_bets_and_has_folded(2)

        players = await PlayersRelation.load_by_table_id(2)
        for player in players:
            self.assertEqual(0, player['bet'])
            self.assertFalse(player['has_folded'])
