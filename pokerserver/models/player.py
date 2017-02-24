from datetime import datetime

from pokerserver.database import PlayersRelation, PlayerState

PLAYER_NAME_PATTERN = "[A-Za-z0-9]{3,}"


class PlayerNotFoundError(Exception):
    pass


class Player:
    # pylint: disable=too-many-instance-attributes
    def __init__(self, table_id, position, name, balance, cards, bet,  # pylint: disable=too-many-arguments
                 last_seen=None, state=PlayerState.PLAYING):
        self.table_id = table_id
        self.position = position
        self.name = name
        self.balance = balance
        self.cards = cards
        self.bet = bet
        self.last_seen = last_seen if last_seen is not None else datetime.now()
        self.state = state

    def __eq__(self, other):
        if not isinstance(other, Player):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self):
        return hash(self.name)

    def to_dict(self, show_cards=False):
        return {
            'table_id': self.table_id,
            'position': self.position,
            'name': self.name,
            'balance': self.balance,
            'cards': self.cards if show_cards else [],
            'bet': self.bet,
            'state': self.state.value
        }

    @classmethod
    async def load_by_name(cls, name):
        player = await PlayersRelation.load_by_name(name)
        if player is not None:
            return Player(**player)
        else:
            raise PlayerNotFoundError()

    @classmethod
    async def load_if_exists(cls, name):
        return await PlayersRelation.load_by_name(name)

    @classmethod
    async def sit_down(cls, table, position, name, balance):  # pylint: disable=too-many-arguments
        await PlayersRelation.add_player(
            table.table_id,
            position,
            name,
            balance,
            cards=[],
            bet=0,
            last_seen=datetime.now(),
            state=PlayerState.PLAYING
        )

    @classmethod
    async def load_by_table_id(cls, table_id):
        players = await PlayersRelation.load_by_table_id(table_id)
        return [cls(**player) for player in players]

    @classmethod
    def is_valid_name(cls, name):
        return name.isalpha()

    @classmethod
    async def reset_bets(cls, table_id):
        await PlayersRelation.reset_bets(table_id)

    @classmethod
    async def reset_after_hand(cls, table_id):
        await PlayersRelation.reset_bets_and_state(table_id)

    async def increase_bet(self, amount):
        assert amount > 0, 'Need to increase bet by more than 0.'
        await PlayersRelation.set_balance_and_bet(self.name, self.balance - amount, self.bet + amount)
        self.balance -= amount
        self.bet += amount
        if self.balance == 0:
            await self.all_in()

    async def increase_balance(self, increase):
        assert increase >= 0, 'the balance increase must not be negative'
        await PlayersRelation.set_balance(self.name, self.balance + increase)
        self.balance += increase

    async def set_cards(self, cards):
        assert len(cards) <= 2
        await PlayersRelation.set_cards(self.name, cards)
        self.cards = cards

    async def fold(self):
        await self.set_state(PlayerState.FOLDED)

    async def all_in(self):
        await self.set_state(PlayerState.ALL_IN)

    def is_all_in(self):
        return self.state == PlayerState.ALL_IN

    async def set_state(self, state):
        self.state = state
        await PlayersRelation.set_state(self.name, self.state)

    def __repr__(self):
        return '<Player {}>'.format(self.name)

    def __str__(self):
        return self.name
