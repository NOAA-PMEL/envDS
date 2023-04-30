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


class Mock(Interface):
    """docstring for Mock."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "type": {"type": "char", "data": "system"},
            "name": {"type": "char", "data": "mock"},
            "description": {
                "type": "char",
                "data": "Simulates a system based interface like serial",
            },
            "tags": {"type": "char", "data": "testing, mock, serial, sensor"},
        },
        "paths": {
            "port-01": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock01"
                },
            },
            "port-02": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock02"
                },
            },
            "port-03": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock03"
                },
            },
            "port-04": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock04"
                },
            },
            "port-05": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock05"
                },
            },
            "port-06": {
                "data": {
                    # "type": "could add type here in case different types of client"
                    "client_module": "envds.daq.clients.mock_client",
                    "client_class": "MockClient",
                    "filepath": "/dev/mock/mock06"
                },
            },
            # "port-02": {
            #     "data": {
            #         "address": {"host": "10.55.169.54", "port": "41"}
            #     }
            # },
            # "port-03": {
            #     "data": {
            #         "uri": "ws://localhost:19292/mock/socket"
            #     }
            # }
            # "port01-1D": {"data": "path/to/port-01"},
            # "port02-2D": {"data": "path/to/port-02"},
            # "port03-i2c": {"data": "path/to/port-03"},
        # }
        }
    }

    def __init__(self, config=None, **kwargs):
        # print("mock:1")
        super(Mock, self).__init__(config=config, **kwargs)
        # print("mock:2")
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_client_module = "envds.daq.clients.mock_client"
        self.default_client_class = "MockClient"

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
        super(Mock, self).configure()

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

            # print("configure:6")
            atts = Mock.metadata["attributes"]

            # print("configure:7")
            path_map = dict()
            for name, val in Mock.metadata["paths"].items():
                # path_map[name] = InterfacePath(name=name, path=val["data"])
                # print("configure:8")

                if "client_module" not in val:
                    val["client_module"] = self.default_client_module
                if "client_class" not in val:
                    val["client_class"] = self.default_client_class
                # print("configure:9")

                client_config = val
                if "path" in conf and name in conf["paths"]:
                    client_config = conf["paths"][name]
                # print("configure:10")
                    
                path_map[name] = {
                    "client_id": name,
                    "client": None,
                    "client_config": client_config,
                    "client_module": val["client_module"],
                    "client_class": val["client_class"],
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
            self.logger.debug("mock:configure", extra={"error": e})


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
        logger.info("mock_test_task", extra={"test": "mock task"})


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
    logger = logging.getLogger("interface::mock::localhost")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    iface = Mock()
    iface.run()
    # task_list.append(asyncio.create_task(iface.run()))
    # await asyncio.sleep(2)
    iface.enable()
    logger.debug("Starting Mock Interface")

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
        logger.debug("mock.run", extra={"do_run": do_run})
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
