import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import sys
import os
import logging
from logfmter import Logfmter
import logging.config
from pydantic import BaseSettings, Field
import json
import yaml
import random
from envds.core import envdsBase, envdsLogger
from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)
# from envds.daq.sensor import Sensor, SensorConfig, SensorVariable
from envds.daq.interface import Interface, InterfaceConfig, InterfacePath
from envds.daq.clients.mock_client import MockClient
from envds.daq.types import DAQEventType
# from envds.event.event import create_data_update, create_status_update
from envds.daq.event import DAQEvent
from envds.message.message import Message
# from typing import Union
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured

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
                }
            },
            "port-02": {
                "data": {
                    "address": {"host": "10.55.169.54", "port": "41"}
                }
            },
            "port-03": {
                "data": {
                    "uri": "ws://localhost:19292/mock/socket"
                }
            }
            # "port01-1D": {"data": "path/to/port-01"},
            # "port02-2D": {"data": "path/to/port-02"},
            # "port03-i2c": {"data": "path/to/port-03"},
        }
    }

    def __init__(self, config=None, **kwargs):
        super(Mock, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_client_module = "envds.daq.clients.mock_client"
        self.default_client_class = "MockClient"

        self.configure()

        self.data_loop_task = None
        print(f"config: {self.config}")
        # self.logger = logging.getLogger(f"{self.config.type}-{self.config.name}-{self.config.uid}")
        self.logger = logging.getLogger(self.build_app_uid())

        # set id
        # self.logger.debug("inherited id", extra={"self.id": self.id})

        # self.update_id("app_uid", f"{self.config.type}-{self.config.name}-{self.config.uid}")
        self.update_id("app_uid", self.build_app_uid())
        self.logger.debug("id", extra={"self.id": self.id})


    def configure(self):
        super(Mock, self).configure()

        '''
        interface.conf: |
            # type: system
            # name: mock
            uid: localhost
            # serial_number: "1234"
            # daq_id: cloudysky
            paths:
                - port-01:
                    client_module: envds.daq.clients.mock_client
                    client_class: MockClient
                    filepath: /dev/mock/iface01
                - port-02:
                    address: 
                    host: 10.55.169.54
                    port: 21
                - port-03:
                    uri: ws://localhost:19292/mock/socket

        '''
        # get config from file
        try:
            with open("/app/config/interface.conf", "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            conf = {"uid": "UNKNOWN", "paths": {}}

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

        atts = Mock.metadata["attributes"]

        path_map = dict()
        for name, val in Mock.metadata["paths"].items():
            # path_map[name] = InterfacePath(name=name, path=val["data"])

            if "client_module" not in val:
                val["client_module"] = self.default_client_module
            if "client_class" not in val:
                val["client_class"] = self.default_client_class

            client_config = val
            if "path" in conf and name in conf["paths"]:
                client_config = conf["paths"][name]
                
            path_map[name] = {
                "client_id": name,
                "client": None,
                "client_config": client_config,
                # "data_buffer": asyncio.Queue(),
                "recv_task": self.recv_data_loop(name),
            }

        self.config = InterfaceConfig(
            type=atts["type"]["data"],
            name=atts["name"]["data"],
            uid=conf["uid"],
            paths=path_map
            # # variables=var_map,
            # interfaces=conf["interfaces"],
            # # daq_id=conf["daq_id"]
        )
        print(f"self.config: {self.config}")

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

    async def recv_data_loop(self, client_id: str):
        
        while True:
            try:
                client = self.config.paths[client_id]["client"]
                while client is not None:
                    data = await client.recv()
                    self.logger.debug("recv_data", extra={"client_id": client_id, "data": data})
                    # TODO: create message and send to subscribers
                    await self.send_data(client_id=client_id, data=data)
                    await asyncio.sleep(.1)
            except KeyError:
                pass

            await asyncio.sleep(5)


    # def start(self):
    #     # print("start: 1")
    #     super(Mock, self).start()
    #     # print("start: 2")

    #     self.data_loop_task = asyncio.create_task(self.data_loop())
    #     # print("start: 3")

    # async def handle_interface_message(self, message: Message):
    #     pass

    # async def handle_serial(self, message: Message):
    #     pass

    # async def parse_serial(self, data: CloudEvent):
    #     pass

    # async def handle_status(self, message: Message):

    #     if message.data["type"] == DAQEvent.status_update():
    #         self.logger.debug("handle_status", extra={"type": DAQEvent.status_request()})
    #         # return status request
    #     pass

    # async def data_loop(self):
    #     # print(f"data_loop:1 - {self.config}")
    #     # generate mock data at the specified data_rate
    #     # put on queue for packaging into cloudevent
    #     # self.logger.info("Starting data_loop", extra=self.extra)
    #     # print("data_loop:1")
    #     # print(f"data_rate: {self.data_rate}")
    #     await asyncio.sleep(time_to_next(self.data_rate))
    #     # print(f"data_rate: {self.data_rate} ready")
    #     while True:
    #         variables = dict()


    #         dt = get_datetime()
    #         dt_str = get_datetime_string()
    #         # print(f"dt: {dt}, {dt_str}")
    #         # self.config.variables["time"]["data"] = dt_str

    #         variables["time"] = dt_str

    #         # variables["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
    #         # variables["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
    #         # variables["altitude"] = round(100 + random.uniform(-10, 10), 3)

    #         variables["temperature"] = str(round(25 + random.uniform(-3, 3), 3))
    #         variables["rh"] = str(round(60 + random.uniform(-5, 5), 3))
    #         variables["pressure"] = str(round(1000 + random.uniform(-5, 5), 3))
    #         variables["wind_speed"] = str(round(10 + random.uniform(-5, 5), 3))
    #         variables["wind_direction"] = str(round(90 + random.uniform(-20, 20), 3))

    #         # print(f"variables: {variables}")
    #         # send_meta = False
    #         # if dt.minute % 10 == 0:
    #         # # if dt.minute % 1 == 0:
    #         #     send_meta = True
    #         # print(f"meta: {send_meta}")
    #         # record = self.build_data_record(meta=send_meta)


    #         # record = self.build_data_record(meta=self.include_metadata)
    #         # self.include_metadata = False
    #         # # print(f"empty record: {record}")
    #         # for name, val in record["variables"].items():
    #         #     # print(name, val)
    #         #     if name in variables:
    #         #         instvar = self.config.variables[name]
    #         #         # print(f"instvar: {instvar}")
    #         #         # print(f"type: {instvar.type}, {eval(instvar.type)(variables[name])}")
    #         #         # print(f"name: {name}, val: {val}, instvar: {instvar}")
    #         #         # record["variables"][name]["data"] = eval(self.config.variables[name]["type"])(variables[name])
    #         #         # record["variables"][name]["data"] = eval(instvar.type)(variables[name])
    #         #         val["data"] = eval(instvar.type)(variables[name])
    #         #         # print(f"record: {record}")



    #         # print(f"data record: {record}")
    #         src = self.get_id_as_source()
    #         # print(src)
    #         event = DAQEvent.create_data_update(
    #             # source="sensor.mockco-mock1-1234", data=record
    #             source=src, data={"test": 1}
    #         )
    #         # print(f"ce: {DAQEvent.data}")
    #         # event = DAQEvent.create_data_update(
    #         #     source="sensor.mockco-mock1-1234", data={"one":"two"}
    #         # )
    #         # event = DAQEvent.create(type="type", source="source", data={"one": "two"})
    #         # print(type(event))
    #         # message=Message(data=event, dest_path="/sensor/mockco/mock1/1234/update")
    #         # message=Message(data=event, dest_path=f"/{src.replace('.', '/')}/update")
    #         self.logger.debug("data record event", extra={"data": event})
    #         message=Message(data=event, dest_path=f"/{self.get_id_as_topic()}/update")
    #         # print(f"to_json: {DAQEvent.data}")
    #         # _, body = to_structured(event)
    #         # print(f"body: {body}")
    #         # print(message.dest_path, to_json(message.data).decode())
            
            
    #         # await self.send_message(message)

    #         # data = {
    #         #     "data": variables,
    #         #     "instance": {"make": "MockCo", "model": "Sensor-1", "serial": self.sn},
    #         # }
    #         # # If we send a message on an even 10-minute mark then
    #         # # include the metadata packet. This is meant to mock
    #         # # occasionally updating a station-sensors's metadata
    #         # if dt.minute % 10 == 0:
    #         #     data["metadata"] = self.metadata
    #         #     data["metadata"]["attributes"] = data["instance"]

    #         # if self.data_buffer:
    #         #     await self.data_buffer.put(data)

    #         await asyncio.sleep(time_to_next(self.data_rate))
    #         # await asyncio.sleep(.1)


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


async def shutdown():
    print("shutting down")
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
    await asyncio.sleep(2)
    iface.enable()
    logger.debug("Starting Mock Interface")

    # get config from file
    uid = "9999"
    try:
        with open("/app/config/interface.conf", "r") as f:
            conf = yaml.safe_load(f)
            try:
                uid = conf["uid"]
            except KeyError:
                pass
    except FileNotFoundError:
        pass

    root_path=f"/envds/interface/system/Mock/{uid}"
    print(f"root_path: {root_path}")

    #TODO: get serial number from config file
    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path=root_path,
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    await server.serve()

    print("starting shutdown...")
    await shutdown()
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
