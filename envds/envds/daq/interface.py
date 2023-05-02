# import abc
import importlib
# import sys
# import uuid
from ulid import ULID
import asyncio
# import logging
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
            await asyncio.sleep(0.1)

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
            await asyncio.sleep(0.1)

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

    # ID_DELIM = "::"

    def __init__(self, config=None, **kwargs):
        super(Interface, self).__init__(config=config, **kwargs)

        self.default_client_module = "unknown"
        self.default_client_class = "unknown"

        # used in loops to add a little delay for async to release
        self.min_recv_delay = 0.1 # seconds

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

    def run_setup(self):
        super().run_setup()
        
        for name, path in self.config.paths.items():
            if name not in self.client_map:
                self.client_map[name] = {
                    "client_id": name,
                    "client": None,
                    "recv_handler": self.config.paths[name]["recv_handler"],
                    "recv_task": None,
                }

        self.logger.debug("run_setup", extra={"client_map": self.client_map})
        self.update_id("app_uid", self.build_app_uid())

    def disable(self):
        
        # remove all subscribers to each client to force disable
        for id, client in self.client_registry.items():
            if self.client_map[id]["client"]:
                self.client_map[id]["client"].disable()
                if self.client_map[id]["recv_task"]:
                    # TODO: these should go in disable logic
                    self.client_map[id]["recv_task"].cancel()
                    self.client_map[id]["recv_task"] = None
                    self.client_map[id]["recv_handler"] = None
            # if client:
            #     client = dict()
        
        super().disable()

    def build_app_uid(self):
        parts = [self.config.type, self.config.name, self.config.uid]
        return (Interface.ID_DELIM).join(parts)

    # these need to start at run
    def set_core_routes(self, enable: bool = True):
        super(Interface, self).set_core_routes()

        topic_base = self.get_id_as_topic()
        self.logger.debug("interface route", extra={"topic_base": topic_base})

        # TODO: remove this route if not needed
        # self.set_route(
        #     subscription=f"{topic_base}/+/connect/request",
        #     route_key=det.interface_connect_request(),
        #     route=self.handle_connect,
        #     enable=enable
        # )

        self.set_route(
            subscription=f"/{topic_base}/+/status/request",
            route_key=det.interface_status_request(),
            route=self.handle_status,
            enable=enable,
        )

        self.logger.debug("set_config_request", extra={"sub": f"/{topic_base}/+/config/request"})
        self.set_route(
            subscription=f"/{topic_base}/+/config/request",
            route_key=det.interface_config_request(),
            route=self.handle_config,
            enable=enable,
        )

        # TODO: remove this route if not needed
        # self.set_route(
        #     subscription=f"{topic_base}/+/connect/keepalive",
        #     route_key=det.interface_connect_keepalive(),
        #     route=self.handle_connect,
        #     enable=enable
        # )

        self.set_route(
            subscription=f"/{topic_base}/+/keepalive/request",
            route_key=det.interface_keepalive_request(),
            route=self.handle_keepalive,
            enable=enable,
        )

        self.set_route(
            subscription=f"/{topic_base}/+/data/send",
            route_key=det.interface_data_send(),
            route=self.handle_data,
            enable=enable,
        )

        # when instantiated, registry should be populated with all possible client_id values

    # def update_client_registry(self, message: Message):
    def update_client_registry(
        self,
        client_id: str,
        source: str,
        keepalive: bool = False,
        deregister: bool = False,
    ):
        self.logger.debug(
            "update_client_registry",
            extra={"client_id": client_id, "source": source, "keepalive": keepalive},
        )
        try:
            if deregister:
                del self.client_registry[client_id][source]
            elif keepalive:
                self.client_registry[client_id][source]["last_update"] = get_datetime()
            else:
                if client_id not in self.client_registry:
                    self.client_registry[client_id] = dict()
                if source not in self.client_registry[client_id]:
                    self.client_registry[client_id][source] = dict()
                self.client_registry[client_id][source]["last_update"] = get_datetime()
                # self.logger.debug(
                #     "client_registry", extra={"reg": self.client_registry}
                # )
        except KeyError:
            pass

        # if message:
        #     source_path = message["source_path"]
        #     client_id = message.data["path_id"]
        #     requested = True
        #     try:
        #         requested = (message.data["requested"] == envdsStatus.TRUE)
        #     except KeyError:
        #         pass

        # try:
        #     if requested:
        #         reg = self.client_registry[client_id]
        #         if source_path in self.client_registry[client_id]:
        #             self.client_registry[client_id][source_path]["last_update"] = get_datetime()
        #             # update time in registry
        #             # pass
        #         else:
        #             self.client_registry[client_id][source_path] = {
        #                 "last_update": get_datetime()
        #             }
        #             # add source_path to registry
        #             # pass
        #     else:
        #         del self.client_registry[client_id][source_path]
        # except KeyError:
        #     pass

    async def client_registry_monitor(self):

        registry_expiration = 10  # if no activity in 5 minutes, expire the connection
        while True:
            try:
                for id, client in self.client_registry.items():
                    # self.logger.debug(
                    #     "registry_monitor", extra={"client_id": id, "client": client}
                    # )
                    for key in list(client.keys()):
                        # if time_expired, del client[key]
                        # self.logger.debug("reg monitor", extra={"key": key})
                        if (
                            seconds_elapsed(client[key]["last_update"])
                            > registry_expiration
                        ):
                            del client[key]
                    self.logger.debug("client_registry_monitor", extra={"id": id, "connections": len(client)})
                    if (
                        len(client) == 0
                    ):  # and self.client_map[client_id].client.connected():
                        self.logger.debug("registry_monitor:2")
                        self.client_map[id]["client"].disable()
                        # if self.client_map[id]["recv_task"]:
                        #     # TODO: these should go in disable logic
                        #     self.client_map[id]["recv_task"].cancel()
                        #     self.client_map[id]["recv_task"] = None
                    else:
                        self.logger.debug("registry_monitor:3")
                        # enable client if needed
                        if not self.client_map[id]["client"].enabled():
                            self.client_map[id]["client"].enable()

                        self.logger.debug("registry_monitor:4")
                        # if self.client_map[id]["recv_task"] is None:
                        #     self.client_map[id]["recv_task"] = asyncio.create_task(
                        #         self.client_map[id]["recv_handler"]
                        #     )
                        #     self.logger.debug(
                        #         "create recv_task",
                        #         extra={"handler": self.client_map[id]["recv_handler"]},
                        #     )
                        self.logger.debug("registry_monitor:5")

                        # send client status update
                        dest_path = f"{self.get_id_as_topic()}/{id}/status/update"
                        extra_header = {"path_id": id}
                        event = DAQEvent.create_status_update(
                            # source="envds.core", data={"test": "one", "test2": 2}
                            source=self.get_id_as_source(),
                            data=self.status.get_status(),
                            extra_header=extra_header,
                        )
                        self.logger.debug("status update", extra={"event": event})
                        message = Message(data=event, dest_path=dest_path)
                        await self.send_message(message)
            except Exception as e:
                self.logger.error("client_registry_monitor", extra={"reg_error": e})
            await asyncio.sleep(2)

    # TODO: remove if not needed
    # async def handle_connect(self, message: Message):

    #     if message.data["type"] == det.interface_connect_keepalive():
    #         self.logger.debug(
    #             "interface connection keepalive",
    #             extra={"source": message.data["source"]},
    #         )
    #         # update connection registry

    #     elif message.data["type"] == det.interface_connect_request():
    #         self.logger.debug(
    #             "interface connection request", extra={"data": message.data}
    #         )
    #         # self.update_client_registry(Message)
    #         #    self.register_client(data=message.data, source_path=message["source_path"])

    #         # parse message.data to get path and connect appropriate client

    async def handle_config(self, message: Message):
        self.logger.debug("interface.handle_config", extra={"config": message.data})
        # self.logger.debug("handle_status:1", extra={"data": message.data})
        # await super(Interface, self).handle_status(message)
        pass

    async def handle_status(self, message: Message):

        # self.logger.debug("handle_status:1", extra={"data": message.data})
        await super(Interface, self).handle_status(message)

        # if message.data["type"] == det.interface_status_request():
        #     self.logger.debug("interface connection keepalive", extra={"source": message.data["source"]})
        #     # update connection registry
        # self.logger.debug("interface handle_status", extra={"data": message.data})
        if message.data["type"] == det.interface_status_request():
            try:
                client_id = message.data["path_id"]
                source = message.data["source"]
                # source_path = message["source_path"]
                state = message.data.data["state"]
                requested = message.data.data["requested"]

                # if state := message.data["state"] == envdsStatus.ENABLED:
                if state == envdsStatus.ENABLED:
                    self.logger.debug(
                        "interface status request", extra={"data": message.data}
                    )
                    # self.update_client_registry(Message)
                    deregister = False
                    if requested != envdsStatus.TRUE:
                        deregister = True
                    self.update_client_registry(
                        client_id=client_id, source=source, deregister=deregister
                    )
                    #    self.register_client(data=message.data, source_path=message["source_path"])
            except KeyError:
                self.logger.error(
                    "unknown interface status request", extra={"data": message.data}
                )

    async def handle_keepalive(self, message: Message):

        if message.data["type"] == det.interface_keepalive_request():

            try:
                client_id = message.data["path_id"]
                source = message.data["source"]
                # source_path = message["source_path"]
                # state = message.data["state"]
                # requested = message.data["requested"]
                self.update_client_registry(
                    client_id=client_id, source=source, keepalive=True
                )
            except KeyError:
                self.logger.error(
                    "unknown keepalive request", extra={"data": message.data}
                )

            self.logger.debug(
                "interface keepalive request", extra={"source": message.data["source"]}
            )
            self.update_client_registry(Message)
            # update connection registry

        # elif message.data["type"] == det.interface_connect_request():
        #     self.logger.debug("interface connection request", extra={"data": message.data})
        #     self.update_client_registry(Message)
        #         #    self.register_client(data=message.data, source_path=message["source_path"])

    # TODO client_id vs id?
    async def update_recv_data(self, client_id: str, data: dict):
        # self.logger.debug("update_recv_data", extra={"client_id": client_id, "data": data})
        dest_path = f"/{self.get_id_as_topic()}/{client_id}/data/update"
        # extra_header = {"source_path": id}
        extra_header = {"path_id": client_id}
        # event = DAQEvent.create_data_update(
        event = DAQEvent.create_interface_data_recv(
            # source="envds.core", data={"test": "one", "test2": 2}
            source=self.get_id_as_source(),
            data=data,
            extra_header=extra_header,
        )
        self.logger.debug("data update", extra={"event": event})
        message = Message(data=event, dest_path=dest_path)
        await self.send_message(message)

    # @abc.abstractmethod
    async def handle_data(self, message: Message):

        # await super(Interface, self).handle_data(message)

        # TODO: handle send data
        if message.data["type"] == det.interface_data_send():
            self.logger.debug(
                "interface data send",
                extra={"dest_path": message["dest_path"], "data": message.data.data},
            )

            # send data to appropriate client

    # async def registry_monitor(self):

    #     while True:

    #         for id, reg in self.client_registry.items():
    #             for src, entry in reg.items():
    #                 # if time delta > timeout, disable client, remove src from reg
    #                 pass

    # async def recv_client_data(self, client_id: str):

    #     while True:
    #         try:
    #             client = self.client_map[client_id]
    #             if client:
    #                 data = await client.recv()
    #                 self.logger.debug("recv client data", extra="client_id")
    #                 # create event and put on send_buffer
    #                 # self.update_recv_data(client_id=client_id, data=data)

    #         except KeyError:
    #             pass

    #         await asyncio.sleep(0.1)

    async def client_monitor(self):

        while True:
            try:
                for id, path in self.config.paths.items():
                    # if path["client"] is None:
                    # if id not in self.client_map:
                    #     self.client_map = {
                    #         self
                    #     }
                    # self.logger.debug(
                    #     "client_monitor",
                    #     extra={
                    #         "client_id": id,
                    #         "path": path,
                    #         "client_map": self.client_map,
                    #     },
                    # )
                    if self.client_map[id]["client"] is None:

                        self.logger.debug(
                            "client_monitor",
                            extra={
                                "client_id": id,
                                "path": path,
                                "client_map": self.client_map,
                            },
                        )

                        try:
                            # print("here:1")
                            client_module = path["client_config"]["attributes"]["client_module"]["data"]
                            # print("here:2")
                            client_class = path["client_config"]["attributes"]["client_class"]["data"]
                            # print("here:3")
                            client_config = DAQClientConfig(uid=id, properties=path["client_config"]["attributes"].copy())
                            # print("here:4")
                            mod_ = importlib.import_module(client_module)
                            # print(f"here:5 {client_module}, {client_class}, {mod_}")
                            # path["client"] = getattr(mod_, client_class)(config=client_config)
                            cls_ = getattr(mod_, client_class)
                            # print(f"here:5.5 {cls_}")
                            self.client_map[id]["client"] = cls_(config=client_config)
                            
                            # TODO: where to start "run"?
                            await asyncio.sleep(1)
                            self.client_map[id]["client"].run()
                            # self.client_map[id]["client"] = getattr(mod_, client_class)(
                            #     config=client_config
                            # )
                            # print(f"here:6 {self.client_map[id]['client']}")


                            if self.client_map[id]["recv_task"] is not None:
                                self.client_map[id]["recv_task"].cancel()

                            self.client_map[id]["recv_task"] = asyncio.create_task(
                                self.client_map[id]["recv_handler"]
                            )
                            self.logger.debug(
                                "create recv_task",
                                extra={"handler": self.client_map[id]["recv_handler"]},
                            )

                        except (KeyError, ModuleNotFoundError, AttributeError) as e:
                            self.logger.error(
                                "client_monitor: could not create client",
                                extra={"error": e},
                            )
                            self.client_map[id]["client"] = None
                    #     self.logger.debug(
                    #         "client_monitor", extra={"client_map": self.client_map}
                    #     )
                    # self.logger.debug("client monitor", extra={"id": id, "path": path})
            except Exception as e:
                self.logger.error("client_monitor", extra={"error": e})
            await asyncio.sleep(5)

    # def run(self):

    #     # initialize client_map
    #     for name, path in self.config.paths.items():
    #         if name not in self.client_map:
    #             self.client_map[name] = {
    #                 "client_id": name,
    #                 "client": None,
    #                 "recv_handler": self.config.paths[name]["recv_handler"],
    #                 "recv_task": None,
    #             }

    #     self.logger.debug("run", extra={"client_map": self.client_map})
    #     super(Interface, self).run()

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
