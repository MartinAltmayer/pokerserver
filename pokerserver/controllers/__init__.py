from .info import InfoController
from .tables import TablesController

_CONTROLLERS = [
    InfoController,
    TablesController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
