from .info import InfoController

_CONTROLLERS = [
    InfoController
]

HANDLERS = [(controller.route, controller) for controller in _CONTROLLERS]
