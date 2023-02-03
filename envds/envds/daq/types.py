from envds.event.types import BaseEventType

# class BaseEventType(object):
class DAQEventType(BaseEventType):
    """docstring for envdsBaseType."""
    TYPE_BASE = "envds"

    TYPE_INTERFACE = "interface"
    TYPE_CONNECT = "connect"

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

    @staticmethod
    def interface_connect_request():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, BaseEventType.ACTION_REQUEST])

    @staticmethod
    def interface_connect_update():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, BaseEventType.ACTION_UPDATE])

    @staticmethod
    def interface_connect_keepalive():
        return ".".join([BaseEventType.get_type(DAQEventType.TYPE_INTERFACE), DAQEventType.TYPE_CONNECT, DAQEventType.ACTION_KEEPALIVE])

