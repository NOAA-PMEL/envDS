import asyncio
import json
import logging 
from ulid import ULID

from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_structured, to_json
from cloudevents.exceptions import InvalidStructuredJSON

# from envds.event.types import BaseEventType as et

from envds.event.event import envdsEvent
from envds.daq.types import DAQEventType as et


class DAQEvent(envdsEvent):
    """docstring for DAQEvent."""
    def __init__(self,):
        super(DAQEvent, self).__init__()

    @staticmethod
    def create_interface_data_recv(source: str, data: dict = {}, extra_header: dict = None):
        return DAQEvent.create(type=et.interface_data_recv(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_interface_data_send(source: str, data: dict = {}, extra_header: dict = None):
        return DAQEvent.create(type=et.interface_data_send(), source=source, data=data, extra_header=extra_header)
    
    # @staticmethod
    # def create_interface_connect_request(source: str, data: dict = {}, extra_header: dict = None):
    #     return DAQEvent.create(type=et.interface_connect_request(), source=source, data=data, extra_header=extra_header)

    # @staticmethod
    # def create_interface_connect_update(source: str, data: dict = {}, extra_header: dict = None):
    #     return DAQEvent.create(type=et.interface_connect_update(), source=source, data=data, extra_header=extra_header)

    # @staticmethod
    # def create_interface_connect_keepalive(source: str, data: dict = {}, extra_header: dict = None):
    #     return DAQEvent.create(type=et.interface_connect_keepalive(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_interface_keepalive_request(source: str, data: dict = {}, extra_header: dict = None):
        return DAQEvent.create(type=et.interface_keepalive_request(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_interface_status_request(source: str, data: dict = {}, extra_header: dict = None):
        return DAQEvent.create(type=et.interface_status_request(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_interface_status_update(source: str, data: dict = {}, extra_header: dict = None):
        return DAQEvent.create(type=et.interface_status_update(), source=source, data=data, extra_header=extra_header)
