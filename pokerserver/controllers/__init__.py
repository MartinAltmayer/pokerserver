from .base import BaseController
from .frontend import FrontendDataController, IndexController, DevCookieController
from .info import InfoController
from .statistics import StatisticsController
from .table import CallController, CheckController, FoldController, JoinController, RaiseController, TableController
from .tables import TablesController
from .uuid import UUIDController

_CONTROLLERS = [
    FrontendDataController,
    IndexController,
    DevCookieController,
    InfoController,
    TableController,
    TablesController,
    JoinController,
    FoldController,
    CallController,
    CheckController,
    RaiseController,
    StatisticsController,
    UUIDController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
