from datetime import datetime

from tornado.testing import gen_test

from pokerserver.database import PlayersRelation, PlayerState, from_card_list
from tests.utils import IntegrationTestCase


class TestPlayersRelation(IntegrationTestCase):
    PLAYER_ROWS = [
        (1, 1, 'player1', 10, 'cards1', 5, datetime.fromtimestamp(123), PlayerState.PLAYING.value),
        (1, 2, 'player2', 20, 'cards2', 10, datetime.fromtimestamp(123), PlayerState.PLAYING.value),
        (2, 3, 'player3', 20, 'cards3', 10, datetime.fromtimestamp(123), PlayerState.PLAYING.value),
        (2, 4, 'player4', 30, 'cards3', 0, datetime.fromtimestamp(123), PlayerState.FOLDED.value)
    ]
    PLAYER_DATA = [{
        'table_id': table_id,
        'position': position,
        'name': name,
        'balance': balance,
        'cards': from_card_list(cards),
        'bet': bet,
        'last_seen': last_seen,
        'state': PlayerState(state)
    } for table_id, position, name, balance, cards, bet, last_seen, state in PLAYER_ROWS]

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
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        new_balance = player_data['balance'] + 100
        await PlayersRelation.set_balance(player_data['name'], new_balance)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_balance, player['balance'])

    @gen_test
    async def test_set_bet(self):
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        new_bet = player_data['bet'] + 100
        await PlayersRelation.set_bet(player_data['name'], new_bet)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_bet, player['bet'])

    @gen_test
    async def test_set_balance_and_bet(self):
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        new_balance = player_data['balance'] + 100
        new_bet = player_data['bet'] + 20
        await PlayersRelation.set_balance_and_bet(player_data['name'], new_balance, new_bet)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(new_balance, player['balance'])
        self.assertEqual(new_bet, player['bet'])

    @gen_test
    async def test_set_cards(self):
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        cards = ['As', '2h']
        assert cards != player_data['cards']
        await PlayersRelation.set_cards(player_data['name'], cards)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(cards, player['cards'])

    @gen_test
    async def test_set_state(self):
        player_data = self.PLAYER_DATA[0]
        await PlayersRelation.add_player(**player_data)
        self.assertEqual(player_data['state'], PlayerState.PLAYING)

        await PlayersRelation.set_state(player_data['name'], PlayerState.FOLDED)

        player = await PlayersRelation.load_by_name(player_data['name'])
        self.assertEqual(player['state'], PlayerState.FOLDED)
