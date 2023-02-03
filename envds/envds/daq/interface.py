import abc
import importlib
import sys
import uuid
from ulid import ULID
import asyncio
import logging
from logfmter import Logfmter

# from typing import Union
from pydantic import BaseModel

from envds.core import envdsBase, envdsStatus
from envds.message.message import Message
from envds.daq.types import DAQEventType as det
from envds.daq.event import DAQEvent
from envds.daq.client import DAQClientConfig


from envds.util.util import get_datetime, seconds_elapsed

class InterfaceClientConfig(BaseModel):
    interface: dict


class InterfacePathConfig(BaseModel):
    name: str
    path: str
    modes: list | None = ["default"]


class InterfacePath(object):
    """docstring for InterfacePath."""

    def __init__(self, config=None):
        super(InterfacePath, self).__init__()

        # message buffers and loops
        self.send_buffer = asyncio.Queue()
        self.recv_buffer = asyncio.Queue()
        self.message_tasks = [
            asyncio.create_task(self.send_loop()),
            asyncio.create_task(self.recv_loop()),
        ]

        self.client = None

    # used by interface to send data to physical sensor
    async def send(self, data: str):
        await self.send_buffer.put(data)

    # processes buffered send data
    async def send_loop(self):

        while True:
            data = await self.send_buffer.get()
            await self.send_data(data)
            await asyncio.sleep(.1)

    # can be overloaded by InterfacePath to handle client specific data
    async def send_data(self, data: str):
        if self.client:
            await self.client.send(data)
        pass

    async def recv(self) -> str:
        return await self.recv_buffer.get()

    async def recv_loop(self) -> str:

        while True:
            data = await self.recv_data()
            await self.recv_buffer.put(data)
            await asyncio.sleep(.1)
            
    async def recv_data(self):
        return await self.client.recv()
    # async def _data(self, data: str):
    #     pass

class InterfaceConfig(BaseModel):
    """docstring for SensorConfig."""

    type: str
    name: str
    uid: str
    paths: dict | None = {}
    # properties: dict | None = {}
    # # variables: list | None = []
    # variables: dict | None = {}
    # interfaces: dict | None = {}
    # daq: str | None = "default"


class Interface(envdsBase):
    """docstring for Interface."""

    CONNECTED = "connected"

    ID_DELIM = "::"

    def __init__(self, config=None, **kwargs):
        super(Interface, self).__init__(config=config, **kwargs)

        self.default_client_module = "unknown"
        self.default_client_class = "unknown"

        # set interface id
        self.update_id("app_group", "interface")
        self.update_id("app_ns", "envds")
        self.update_id("app_uid", f"interface-id-{ULID()}")
        self.logger.debug("interface id", extra={"self.id": self.id})

        self.status.set_id_AppID(self.id)
        # self.status.set_state_param(
        #     Interface.CONNECTED, requested=envdsStatus.FALSE, actual=envdsStatus.FALSE
        # )

        self.client_registry = {
            # client_id: {
            #     source_path1: {"last_update": timestamp},
            #     source_path2: {"last_update": timestamp}
            # }
        }

        self.client_map = {
            # name: {
            #     "client_id": "",
            #     "client": None, # will be MockClient()
            #     "recv_task": None # will be asyncio task create to read client
            # }
        }
        self.run_task_list.append(self.client_monitor())
        self.run_task_list.append(self.client_registry_monitor())

        # add connect to enable_task_list
        # add data loop to enable task list

    def configure(self):
        super(Interface, self).configure()
        self.logger.debug("configure()")

    def build_app_uid(self):
        parts = [
            self.config.type,
            self.config.name,
            self.config.uid
        ]
        return (Interface.ID_DELIM).join(parts)

    def set_routes(self, enable: bool = True):
        super(Interface, self).set_routes()

        topic_base = self.get_id_as_topic()
        self.logger.debug("interface route", extra={"topic_base": topic_base})

        self.set_route(
            subscription=f"{topic_base}/+/connect/request",
            route_key=det.interface_connect_request(),
            route=self.handle_connect,
            enable=enable
        )

        self.set_route(
            subscription=f"{topic_base}/+/connect/keepalive",
            route_key=det.interface_connect_keepalive(),
            route=self.handle_connect,
            enable=enable
        )

        self.set_route(
            subscription=f"{topic_base}/+/data/send",
            route_key=det.interface_data_send(),
            route=self.handle_data,
            enable=enable
        )

        # when instantiated, registry should be populated with all possible client_id values

    def update_client_registry(self, message: Message):
        
        if message:
            source_path = message["source_path"]
            client_id = message.data["path_id"]
            try:
                reg = self.client_registry[client_id]
                if source_path in self.client_registry[client_id]:
                    self.client_registry[client_id][source_path]["last_update"] = get_datetime()
                    # update time in registry
                    # pass
                else:
                    self.client_registry[client_id][source_path] = {
                        "last_update": get_datetime()
                    }
                    # add source_path to registry
                    # pass
            except KeyError:
                pass

    async def client_registry_monitor(self):

        registry_expiration = 300 # if no activity in 5 minutes, expire the connection

        for id, client in self.client_registry.items():
            for key in list(client.keys()):
                # if time_expired, del client[key]
                if seconds_elapsed(client[key]["last_update"]) > registry_expiration:
                    del client[key]
                
            if len(client) == 0: # and self.client_map[client_id].client.connected():
                self.client_map[id]["client"].disable()
                if self.client_map[id]["recv_task"]:
                    # TODO: these should go in disable logic
                    self.client_map[id]["recv_task"].cancel()
                    self.client_map[id]["recv_task"] = None
            else:
                # enable client if needed
                if not client.enabled()
                    client.enable()

                # send client status update
                dest_path = f"{self.get_id_as_topic()}/{id}/status/update"
                extra_header = {"source_path": id}
                event = DAQEvent.create_status_update(
                    # source="envds.core", data={"test": "one", "test2": 2}
                    source=self.get_id_as_source(),
                    data=self.status.get_status(),
                    extra_header=extra_header
                )
                self.logger.debug("status update", extra={"event": event})
                message = Message(data=event, dest_path=dest_path)
                await self.send_message(message)


        await asyncio.sleep(5)

    
    async def handle_connect(self, message: Message):

        if message.data["type"] == det.interface_connect_keepalive():
            self.logger.debug("interface connection keepalive", extra={"source": message.data["source"]})
            # update connection registry

        elif message.data["type"] == det.interface_connect_request():
            self.logger.debug("interface connection request", extra={"data": message.data})
            try:
                if message.data["enable"] == envdsStatus.TRUE:
                    self.register_client(data=message.data, source_path=message["source_path"])


            # parse message.data to get path and connect appropriate client

    async def send_data(self, client_id: str, data: dict):
        dest_path = f"{self.get_id_as_topic()}/{id}/data/update"
        extra_header = {"source_path": id}
        event = DAQEvent.create_data_update(
            # source="envds.core", data={"test": "one", "test2": 2}
            source=self.get_id_as_source(),
            data=data,
            extra_header=extra_header
        )
        self.logger.debug("data update", extra={"event": event})
        message = Message(data=event, dest_path=dest_path)
        await self.send_message(message)


    # @abc.abstractmethod
    async def handle_data(self, message: Message):
        
        if message.data["type"] == det.interface_data_send():
            self.logger.debug("interface data send", extra={"dest_path": message["dest_path"], "data": message.data.data})

            # send data to appropriate client

    async def registry_monitor(self):

        while True:

            for id, reg in self.client_registry.items():
                for src, entry in reg.items():
                    # if time delta > timeout, disable client, remove src from reg
                    pass


    async def recv_client_data(self, client_id: str):
        
        while True:
            try:
                client = self.client_map[client_id]
                if client:
                    data = await client.recv()
                    self.logger.debug("recv client data", extra="client_id")
                    # create event and put on send_buffer

            except KeyError:
                pass
                
            await asyncio.sleep(.1)

    async def client_monitor(self):

        while True:
            for id, path in self.config.paths.items():
                if path["client"] is None:
                    try:
                        client_module = path["client_config"]["client_module"]
                        client_class = path["client_config"]["client_class"]
                        client_config = DAQClientConfig(uid=id)
                        mod_ = importlib.import_module(client_module)
                        path["client"] = getattr(mod_, client_class)
                    except (KeyError, ModuleNotFoundError, AttributeError) as e:
                        self.logger.error("client_monitor: could not create client", extra={"error": e})
            
                self.logger.debug("client monitor", extra={"id": id, "path": path} )
            await asyncio.sleep(5)

        # self.message_client.subscribe(f"{topic_base}/connect/request")
        # self.router.register_route(
        #     key=det.interface_connect_request(), route=self.handle_connect
        # )

        # self.message_client.subscribe(f"{topic_base}/connect/keepalive")
        # self.router.register_route(
        #     key=det.interface_connect_keepalive(), route=self.handle_connect
        # )

        # self.message_client.subscribe(f"{topic_base}/data/send")
        # self.router.register_route(
        #     key=det.interface_data_send(), route=self.handle_data
        # )

        # self.message_client.subscribe(f"{topic_base}/status/update")
        # self.message_client.subscribe(f"{topic_base}/status/update/#")
        # self.router.register_route(key=det.status_update(), route=self.handle_data)

        # self.message_client.subscribe(f"{topic_base}/status/update")
        # self.message_client.subscribe(f"{topic_base}/status/update/#")
        # self.router.register_route(key=det.status_update(), route=self.handle_data)

    # def enable(self):
    #     pass

    # def disable(self):
    #     pass

    # def start(self):
    #     self.enable()
    #     self.run_state = "STARTING"
    #     self.logger.debug("start", extra={"run_state": self.run_state})

    # def stop(self):
    #     pass
