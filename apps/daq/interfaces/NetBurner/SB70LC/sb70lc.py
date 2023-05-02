import asyncio
import signal
# import uvicorn
# from uvicorn.config import LOGGING_CONFIG
import sys
import os
import logging
# from logfmter import Logfmter
import logging.config
# from pydantic import BaseSettings, Field
# import json
import yaml
# import random
from envds.core import envdsLogger #, envdsBase 
# from envds.util.util import (
#     get_datetime_format,
#     time_to_next,
#     get_datetime,
#     get_datetime_string,
# )
# from envds.daq.sensor import Sensor, SensorConfig, SensorVariable
from envds.daq.interface import Interface, InterfaceConfig #, InterfacePath
# from envds.daq.clients.mock_client import MockClient
# from envds.daq.types import DAQEventType
# from envds.event.event import create_data_update, create_status_update
# from envds.daq.event import DAQEvent
# from envds.message.message import Message
# from typing import Union
# from cloudevents.http import CloudEvent, from_dict, from_json
# from cloudevents.conversion import to_json, to_structured

from pydantic import BaseModel

task_list = []


class SB70LC(Interface):
    """docstring for SB70LC."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "type": {"type": "char", "data": "NetBurner"},
            "name": {"type": "char", "data": "SB70LC"},
            "host": {"type": "char", "data": "localhost"},
            "description": {
                "type": "char",
                "data": "Netburner SB70LC serial to ethernet server with i2c",
            },
            "tags": {"type": "char", "data": "testing, netburner, SB70LC, serial, tcp, ethernet, i2c, sensor"},
        },
        "paths": {
            "port-1": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 23},
                },
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.tcp_client",
                    "client_class": "TCPClient",
                    "address": {"host": "localhost", "port": 23}
                },
            },
            "port-2": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 24},
                },
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.tcp_client",
                    "client_class": "TCPClient",
                    "address": {"host": "localhost", "port": 24}
                },
            },
            "port-I2C": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 26},
                },
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.tcp_client",
                    "client_class": "TCPClient",
                    "address": {"host": "localhost", "port": 26}
                },
            },
        }
    }

    def __init__(self, config=None, **kwargs):
        # print("mock:1")
        super(SB70LC, self).__init__(config=config, **kwargs)
        # print("mock:2")
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_client_module = "envds.daq.clients.tcp_client"
        self.default_client_class = "TCPClient"

        self.data_loop_task = None
        # print("mock:3")

        # handled in run_setup ----
        # self.configure()

        # print(f"config: {self.config}")
        # # self.logger = logging.getLogger(f"{self.config.type}-{self.config.name}-{self.config.uid}")
        # self.logger = logging.getLogger(self.build_app_uid())

        # # set id
        # # self.logger.debug("inherited id", extra={"self.id": self.id})

        # # self.update_id("app_uid", f"{self.config.type}-{self.config.name}-{self.config.uid}")
        # self.update_id("app_uid", self.build_app_uid())
        # self.logger.debug("id", extra={"self.id": self.id})
        # ----


    def configure(self):

        # print("configure:1")
        super(SB70LC, self).configure()

        try:
            # get config from file
            # print("configure:2")
            try:
                # print("configure:3")
                with open("/app/config/interface.conf", "r") as f:
                    conf = yaml.safe_load(f)
                # print("configure:4")
            except FileNotFoundError:
                conf = {"uid": "UNKNOWN", "paths": {}}

            # add hosts to each path if not present
            try:
                host = conf["host"]
            except KeyError as e:
                self.logger.debug("no host - default to localhost")
                host = "localhost"
            for name, path in conf["paths"].items():
                if "host" not in path:
                    path["host"] = host

            # print("configure:5")
            self.logger.debug("conf", extra={"data": conf})
            # if "metadata_interval" in conf:
            #     self.include_metadata_interval = conf["metadata_interval"]

            # # create SensorConfig      
            # var_list = []
            # var_map = dict()
            # for name, val in Mock.metadata["variables"].items():
            #     var_list.append(
            #         SensorVariable(
            #             name=name,
            #             type=val["type"],
            #             shape=val["shape"],
            #             attributes=val["attributes"],
            #         )
            #     )
            #     var_map[name] = SensorVariable(
            #         name=name,
            #         type=val["type"],
            #         shape=val["shape"],
            #         attributes=val["attributes"],
            #     )
            # # print(f"var_list: {var_list}")

            # TODO: configure Interface
            # TODO: configure each path(client)

            # print("configure:6")
            atts = SB70LC.metadata["attributes"]

            # print("configure:7")
            path_map = dict()
            for name, val in SB70LC.metadata["paths"].items():
                # path_map[name] = InterfacePath(name=name, path=val["data"])
                # print("configure:8")

                if "client_module" not in val["attributes"]:
                    val["attributes"]["client_module"]["data"] = self.default_client_module
                if "client_class" not in val["attributes"]:
                    val["attributes"]["client_class"]["data"] = self.default_client_class
                # print("configure:9")

                # set path host from interface attributes
                if "host" in atts:
                    val["attributes"]["host"]["data"] = atts["host"]

                client_config = val
                # override values from yaml config
                if "paths" in conf and name in conf["paths"]:
                    self.logger.debug("yaml conf", extra={"id": name, "conf['paths']": conf['paths'], })
                    for attname, attval in conf["paths"][name].items():
                        self.logger.debug("config paths", extra={"id": name, "attname": attname, "attval": attval})
                        client_config["attributes"][attname]["data"] = attval
                # print("configure:10")
                self.logger.debug("config paths", extra={"client_config": client_config})
                    
                path_map[name] = {
                    "client_id": name,
                    "client": None,
                    "client_config": client_config,
                    "client_module": val["attributes"]["client_module"]["data"],
                    "client_class": val["attributes"]["client_class"]["data"],
                    # "data_buffer": asyncio.Queue(),
                    "recv_handler": self.recv_data_loop(name),
                    "recv_task": None,
                }
            # print("configure:11")

            self.config = InterfaceConfig(
                type=atts["type"]["data"],
                name=atts["name"]["data"],
                uid=conf["uid"],
                paths=path_map
                # # variables=var_map,
                # interfaces=conf["interfaces"],
                # # daq_id=conf["daq_id"]
            )
            # print(f"self.config: {self.config}")

            self.logger.debug(
                "configure",
                extra={"conf": conf, "self.config": self.config},
            )

            # async def recv_data_loop():
            #     while True:
            #         if self.enabled()


            # if "interfaces" in self.config:
            #     for name, iface in conf.items():
            #         self.iface_map[name] = iface
            #         # if name == "default":
            #         #     pass
            #         # elif name == "serial":
            #         #     iface["dest_path"] = f"/envds/interface/{iface[]}"
        except Exception as e:
            self.logger.debug("sb70lc:configure", extra={"error": e})


    async def recv_data_loop(self, client_id: str):
        
        # self.logger.debug("recv_data_loop", extra={"client_id": client_id})
        while True:
            try:
                # client = self.config.paths[client_id]["client"]
                client = self.client_map[client_id]["client"]
                # while client is not None:
                if client:
                    self.logger.debug("recv_data_loop", extra={"client": client})
                    data = await client.recv()
                    self.logger.debug("recv_data", extra={"client_id": client_id, "data": data})

                    await self.update_recv_data(client_id=client_id, data=data)
                    # await asyncio.sleep(self.min_recv_delay)
                else:
                    await asyncio.sleep(1)
            except (KeyError, Exception) as e:
                self.logger.error("recv_data_loop", extra={"error": e})
                await asyncio.sleep(1)

            # await asyncio.sleep(self.min_recv_delay)
            await asyncio.sleep(0.1)

class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("sb70lc_test_task", extra={"test": "sb70lc task"})


async def shutdown(interface):
    print("shutting down")

    if interface:
        await interface.shutdown()

    for task in task_list:
        print(f"cancel: {task}")
        task.cancel()


async def main(server_config: ServerConfig = None):
    # uiconfig = UIConfig(**config)
    if server_config is None:
        server_config = ServerConfig()
    print(server_config)

    # print("starting mock1 test task")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("interface::sb70lc::53")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    iface = SB70LC()
    iface.run()
    # task_list.append(asyncio.create_task(iface.run()))
    # await asyncio.sleep(2)
    iface.enable()
    logger.debug("Starting SB70LC Interface")

    # remove fastapi ----
    # # get config from file
    # uid = "9999"
    # try:
    #     with open("/app/config/interface.conf", "r") as f:
    #         conf = yaml.safe_load(f)
    #         try:
    #             uid = conf["uid"]
    #         except KeyError:
    #             pass
    # except FileNotFoundError:
    #     pass

    # root_path=f"/envds/interface/system/Mock/{uid}"
    # # print(f"root_path: {root_path}")

    # config = uvicorn.Config(
    #     "main:app",
    #     host=server_config.host,
    #     port=server_config.port,
    #     log_level=server_config.log_level,
    #     root_path=root_path,
    #     # log_config=dict_config,
    # )

    # server = uvicorn.Server(config)
    # # test = logging.getLogger()
    # # test.info("test")
    # await server.serve()
    # ----

    event_loop = asyncio.get_event_loop()
    global do_run 
    do_run = True
    def shutdown_handler(*args):
        global do_run
        do_run = False

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    while do_run:
        logger.debug("sb70lc.run", extra={"do_run": do_run})
        await asyncio.sleep(1)


    print("starting shutdown...")
    # await iface.shutdown()
    await shutdown(iface)
    # await asyncio.sleep(2)
    print("done.")


if __name__ == "__main__":

    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.path.dirname(os.path.abspath(__file__))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    print(sys.argv)
    config = ServerConfig()
    try:
        index = sys.argv.index("--host")
        host = sys.argv[index + 1]
        config.host = host
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--port")
        port = sys.argv[index + 1]
        config.port = int(port)
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--log_level")
        ll = sys.argv[index + 1]
        config.log_level = ll
    except (ValueError, IndexError):
        pass

    asyncio.run(main(config))
