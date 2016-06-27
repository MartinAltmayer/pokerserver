from uuid import uuid4
from tornado.testing import gen_test

from pokerserver.database import UUIDsRelation
from tests.integration.utils.integration_test import IntegrationTestCase


class TestUUIDsRelation(IntegrationTestCase):
    PLAYERS = {
        uuid4(): 'frodo',
        uuid4(): 'gandalf'
    }

    @gen_test
    async def test_add_uuid(self):
        uuid = uuid4()
        await UUIDsRelation.add_uuid(uuid, 'lancelot')
        row = await self.db.find_row('SELECT uuid, player_name FROM uuids')
        self.assertEqual((str(uuid), 'lancelot'), row)

    @gen_test
    async def test_load_by_uuid(self):
        uuid = uuid4()
        await UUIDsRelation.add_uuid(uuid, 'robin')

        data = await UUIDsRelation.load_by_uuid(uuid)
        self.assertEqual({'uuid': str(uuid), 'player_name': 'robin'}, data)


    @gen_test
    async def test_load_all(self):
        for uuid, player_name in self.PLAYERS.items():
            await UUIDsRelation.add_uuid(uuid, player_name)
        actual_uuids = await UUIDsRelation.load_all()
        self.assertDictEqual(self.PLAYERS, actual_uuids)
