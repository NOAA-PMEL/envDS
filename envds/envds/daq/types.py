from envds.event.types import BaseEventType

# class BaseEventType(object):
class DAQEventType(BaseEventType):
    """docstring for envdsBaseType."""
    TYPE_BASE = "envds"

    TYPE_SENSOR = "sensor"
    TYPE_SETTINGS = "settings"
    TYPE_INTERFACE = "interface"
    TYPE_CONNECT = "connect"
    TYPE_CONFIG = "config"
    
    ACTION_RECV = "recv"
    ACTION_SEND = "send"
    ACTION_KEEPALIVE = "keepalive"

    def __init__(self):
        super(BaseEventType, self).__init__()

    # helper functions

    @staticmethod
    def interface_data_recv():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), BaseEventType.TYPE_DATA, DAQEventType.ACTION_RECV])

    @staticmethod
    def interface_data_send():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), BaseEventType.TYPE_DATA, DAQEventType.ACTION_SEND])

    # @staticmethod
    # def interface_connect_request():
    #     return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, BaseEventType.ACTION_REQUEST])

    # @staticmethod
    # def interface_connect_update():
    #     return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, BaseEventType.ACTION_UPDATE])

    # @staticmethod
    # def interface_connect_keepalive():
    #     return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, DAQEventType.ACTION_KEEPALIVE])

    @staticmethod
    def interface_keepalive_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_KEEPALIVE, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def interface_config_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONFIG, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def interface_status_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_STATUS, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def interface_status_update():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_STATUS, DAQEventType.ACTION_UPDATE])

    @staticmethod
    def sensor_registry_update():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_SENSOR), DAQEventType.TYPE_REGISTRY, DAQEventType.ACTION_UPDATE])

    @staticmethod
    def sensor_registry_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_SENSOR), DAQEventType.TYPE_REGISTRY, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def interface_registry_update():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_REGISTRY, DAQEventType.ACTION_UPDATE])

    @staticmethod
    def interface_registry_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_REGISTRY, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def sensor_settings_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_SENSOR), DAQEventType.TYPE_SETTINGS, DAQEventType.ACTION_REQUEST])

    @staticmethod
    def sensor_settings_update():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_SENSOR), DAQEventType.TYPE_SETTINGS, DAQEventType.ACTION_UPDATE])
