from .database import Database, DbException
from .stats import StatsRelation
from .tables import TablesRelation
from .uuids import UUIDsRelation

RELATIONS = [TablesRelation, StatsRelation, UUIDsRelation]
