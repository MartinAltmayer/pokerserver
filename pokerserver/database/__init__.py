from .database import Database, DbException
from .players import PlayersRelation
from .stats import StatsRelation
from .tables import TablesRelation
from .uuids import UUIDsRelation

RELATIONS = [PlayersRelation, TablesRelation, StatsRelation, UUIDsRelation]
