from pokerserver.api import API_SPECIFICATION
from .api import ApiController, ApiDocsController
from .base import BaseController
from .frontend import DevCookieController, FrontendDataController, IndexController
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
    UUIDController,
    ApiController,
    ApiDocsController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]

for handler in HANDLERS:
    API_SPECIFICATION.add_path(urlspec=handler)
