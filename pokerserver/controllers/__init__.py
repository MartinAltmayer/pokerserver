from .info import InfoController
from .table import TableController, JoinController, FoldController, CallController
from .tables import TablesController
from .uuid import UUIDController

_CONTROLLERS = [
    InfoController,
    TableController,
    TablesController,
    JoinController,
    FoldController,
    CallController,
    UUIDController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
