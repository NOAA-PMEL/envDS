class BaseEventType(object):
    """docstring for envdsBaseType."""
    TYPE_BASE = "envds"

    TYPE_DATA = "data"
    TYPE_STATUS = "status"
    TYPE_REGISTRY = "registry"
    TYPE_SERVICE = "service"
    TYPE_CONTROL = "control"
    TYPE_MANAGE = "manage"
    TYPE_PING = "ping"
    TYPE_KEEPALIVE = "keepalive"

    ACTION_REQUEST = "request"
    ACTION_UPDATE = "update"
    ACTION_BCAST = "broadcast"

    def __init__(self):
        super(BaseEventType, self).__init__()

    # helper functions
    @staticmethod
    def data_update():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_DATA), BaseEventType.ACTION_UPDATE])

    @staticmethod
    def status_update():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_STATUS), BaseEventType.ACTION_UPDATE])
    @staticmethod
    def status_request():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_STATUS), BaseEventType.ACTION_REQUEST])

    @staticmethod
    def registry_bcast():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_REGISTRY), BaseEventType.ACTION_BCAST])

    @staticmethod
    def registry_update():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_REGISTRY), BaseEventType.ACTION_UPDATE])

    @staticmethod
    def registry_request():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_REGISTRY), BaseEventType.ACTION_REQUEST])
    
    @staticmethod
    def control_request():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_CONTROL), BaseEventType.ACTION_REQUEST])

    @staticmethod
    def control_update():
        return ".".join([BaseEventType.TYPE_BASE, BaseEventType.TYPE_CONTROL, BaseEventType.ACTION_UPDATE])

    @staticmethod
    def keepalive_request():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_KEEPALIVE), BaseEventType.ACTION_REQUEST])

    @staticmethod
    def keepalive_update():
        return ".".join([BaseEventType.TYPE_BASE, BaseEventType.TYPE_KEEPALIVE, BaseEventType.ACTION_UPDATE])

    @staticmethod
    def service_registry_update():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_SERVICE), BaseEventType.TYPE_REGISTRY, BaseEventType.ACTION_UPDATE])

    @staticmethod
    def service_registry_request():
        return ".".join([BaseEventType.get_type(BaseEventType.TYPE_SERVICE), BaseEventType.TYPE_REGISTRY, BaseEventType.ACTION_REQUEST])

    @staticmethod
    def get_type(type: str):
        return ".".join([BaseEventType.TYPE_BASE, type])

    @staticmethod
    def parse_event_type(type: str):
        parts = type.split(".")
        action = parts.pop(-1)
        et = ".".join(parts)
        return et, action
