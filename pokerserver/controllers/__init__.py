from .info import InfoController
from .table import TableController
from .tables import TablesController

_CONTROLLERS = [
    InfoController,
    TableController,
    TablesController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
