from unittest import TestCase

from pokerserver.models import Table


class PotChecker(TestCase):
    async def assert_pots(self, table_name, amounts=None):
        if amounts is None:
            amounts = [0]
        table = await Table.load_by_name(table_name)
        self.assertEqual(amounts, [pot.amount for pot in table.pots])
