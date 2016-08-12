from .info import InfoController
from .table import TableController, JoinController, FoldController, CallController, CheckController, RaiseController
from .tables import TablesController
from .uuid import UUIDController

_CONTROLLERS = [
    InfoController,
    TableController,
    TablesController,
    JoinController,
    FoldController,
    CallController,
    CheckController,
    RaiseController,
    UUIDController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
