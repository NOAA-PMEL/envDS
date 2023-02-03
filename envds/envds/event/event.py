import asyncio
import json
import logging 
from ulid import ULID

from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_structured, to_json
from cloudevents.exceptions import InvalidStructuredJSON

from envds.event.types import BaseEventType as et


class envdsEvent(object):
    """docstring for envdsEvent."""

    def __init__(self):
        super(envdsEvent, self).__init__()
        # self.logger = logging.getLogger(self.__class__.__name__)

    def create(type: str, source: str, data: dict = {}, extra_header: dict = None) -> CloudEvent:

        attributes = {
            "type": type,
            "source": source,
            "id": str(ULID()),
            "datacontenttype": "application/json; charset=utf-8",
        }

        if extra_header:
            for k,v in extra_header.items():
                attributes[k] = v

        try:
            # payload = data
            ce = CloudEvent(attributes=attributes, data=data)
            return ce
        except Exception as e:
            logging.getLogger(__name__).error("envdsEvent.create", extra={"error": e})
            print(f"error creating cloud event: {e}")
            return None

    # helper functions

    @staticmethod
    def create_data_update(source: str, data: dict = {}, extra_header: dict = None):
        return envdsEvent.create(type=et.data_update(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_status_update(source: str, data: dict = {}, extra_header: dict = None):
        return envdsEvent.create(type=et.status_update(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_status_request(source: str, data: dict = {}, extra_header: dict = None):
        return envdsEvent.create(type=et.status_request(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_control_request(source: str, data: dict = {}, extra_header: dict = None):
        return envdsEvent.create(type=et.control_request(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_control_update(source: str, data: dict = {}, extra_header: dict = None):
        return envdsEvent.create(type=et.control_update(), source=source, data=data, extra_header=extra_header)

    @staticmethod
    def create_ping(source: str, data: dict = {"data": "ping"}, extra_header: dict = None):
        return envdsEvent.create(type=et.TYPE_PING, source=source, data=data, extra_header=extra_header)


# Future: allow for partial routes to match:
#   e.g., route = envds.status would match envds.status.request and envds.status.update
class EventRouter(object):
    """docstring for EventRouter."""
    def __init__(self):
        super(EventRouter, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.routes = dict()

    def register_route(self, key: str, route, allow_partial: bool = False):
        self.routes[key] = {
            "route": route,
            "allow_partial": allow_partial
        }
        # print(f"register_route: {key}, {route}, {self.routes}")
        self.logger.debug("register_route", extra={"key": key, "route": route})

    def deregister_route(self, key: str):
        if key in self.routes:
            self.routes.pop(key)

    def route_event(self, event: CloudEvent):
        # print(f"route_event: {event}")
        try:
            # self.logger.debug("route_event", extra={"type": type(event)})#, "routes": self.routes})
            return self.get_route(event["type"])
        except Exception as e:
            self.logger.debug("route_event", extra={"exception": e})
            return None


    def get_route(self, key: str):
        print(f"get_route: {key}")
        try:
            # self.logger.debug("get_route", extra={"key", key})
            return self.routes[key]["route"]
        except KeyError:
            # print(f"key error: {type(self.routes)}")
            if self.routes[key]["allow_partial"]:
                for k,v in self.routes.items():
                    if key in k:
                        return k["route"]
            else:
                return None