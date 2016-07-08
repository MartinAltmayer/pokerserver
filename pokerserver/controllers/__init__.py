from pokerserver.controllers.table import JoinController, FoldController
from pokerserver.controllers.uuid import UUIDController
from .info import InfoController
from .table import TableController
from .tables import TablesController

_CONTROLLERS = [
    InfoController,
    TableController,
    TablesController,
    JoinController,
    FoldController,
    UUIDController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
