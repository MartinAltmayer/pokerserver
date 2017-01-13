from .players import PlayersRelation
from .stats import StatsRelation
from .tables import TablesRelation
from .uuids import UUIDsRelation

RELATIONS = [PlayersRelation, TablesRelation, StatsRelation, UUIDsRelation]


async def clear_relations(exclude=None):
    if exclude is None:
        exclude = []
    for table_class in RELATIONS:
        if table_class.NAME not in exclude:
            await table_class.clear_relation()


async def create_relations():
    for table_class in RELATIONS:
        await table_class.drop_relation()
        await table_class.create_relation()
