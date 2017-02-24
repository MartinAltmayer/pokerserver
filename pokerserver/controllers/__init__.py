from .base import BaseController
from .frontend import IndexController, FrontendDataController
from .info import InfoController
from .table import CallController, CheckController, FoldController, JoinController, RaiseController, TableController
from .tables import TablesController
from .uuid import UUIDController

_CONTROLLERS = [
    FrontendDataController,
    IndexController,
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
