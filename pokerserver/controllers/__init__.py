from pokerserver.controllers.table import JoinController
from pokerserver.controllers.uuid import UUIDController
from .info import InfoController
from .table import TableController
from .tables import TablesController

_CONTROLLERS = [
    InfoController,
    TableController,
    TablesController,
    JoinController,
    UUIDController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
