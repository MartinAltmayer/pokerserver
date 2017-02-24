from pokerserver.models import Table
from .integration_test import IntegrationTestCase


class PotChecker(IntegrationTestCase):
    async def assert_pots(self, table_name, amounts=None):
        if amounts is None:
            amounts = [0]
        table = await Table.load_by_name(table_name)
        self.assertEqual(amounts, [pot.amount for pot in table.pots])
