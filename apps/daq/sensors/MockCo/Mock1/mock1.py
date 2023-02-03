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
from envds.core import envdsBase, envdsLogger, envdsStatus
from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)
from envds.daq.sensor import Sensor, SensorConfig, SensorVariable
# from envds.event.event import create_data_update, create_status_update
from envds.event.event import envdsEvent as et
from envds.message.message import Message
from envds.exceptions import envdsRunTransitionException
# from typing import Union
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured

from pydantic import BaseModel

task_list = []


class Mock1(Sensor):
    """docstring for Mock1."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "char", "data": "MockCo"},
            "model": {"type": "char", "data": "Mock1"},
            "description": {
                "type": "char",
                "data": "Simulates a meterological type of sensor for the purposes of testing. Data records are emitted once per second.",
            },
            "tags": {"type": "char", "data": "testing, mock, meteorology, sensor"},
        },
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": "Time"},
            },
            "temperature": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Temperature", "units": "degree_C"},
            },
            "rh": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "RH", "units": "percent"},
            },
            "pressure": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Pressure", "units": "hPa"},
            },
            "wind_speed": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Wind Speed", "units": "m s-1"},
            },
            "wind_direction": {
                "type": "float",
                "shape": ["time"],
                "attributes": {"long_name": "Wind Direction", "units": "degree"},
            },
        },
    }

    def __init__(self, config=None, **kwargs):
        super(Mock1, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        # self.data_loop_task = None

        self.configure()

        # self.logger = logging.getLogger(f"{self.config.make}-{self.config.model}-{self.config.serial_number}")
        self.logger = logging.getLogger(self.build_app_uid())

        # self.update_id("app_uid", f"{self.config.make}-{self.config.model}-{self.config.serial_number}")
        self.update_id("app_uid", self.build_app_uid())

        # self.logger.debug("id", extra={"self.id": self.id})
        print(f"config: {self.config}")

        self.sampling_task_list.append(self.data_loop())

    def configure(self):
        super(Mock1, self).configure()

        # get config from file
        try:
            with open("/app/config/sensor.conf", "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            conf = {"serial_number": "UNKNOWN", "interfaces": {}}

        if "metadata_interval" in conf:
            self.include_metadata_interval = conf["metadata_interval"]

        # create SensorConfig      
        var_list = []
        var_map = dict()
        for name, val in Mock1.metadata["variables"].items():
            var_list.append(
                SensorVariable(
                    name=name,
                    type=val["type"],
                    shape=val["shape"],
                    attributes=val["attributes"],
                )
            )
            var_map[name] = SensorVariable(
                name=name,
                type=val["type"],
                shape=val["shape"],
                attributes=val["attributes"],
            )
        # print(f"var_list: {var_list}")

        atts = Mock1.metadata["attributes"]
        self.config = SensorConfig(
            make=atts["make"]["data"],
            model=atts["model"]["data"],
            serial_number=conf["serial_number"],
            variables=var_map,
            interfaces=conf["interfaces"],
            daq_id=conf["daq_id"]
        )
        print(f"self.config: {self.config}")

        self.logger.debug(
            "configure",
            extra={"conf": conf, "var_map": var_map, "self.config": self.config},
        )

        if "interfaces" in self.config:
            for name, iface in conf.items():
                self.iface_map[name] = iface

        self.logger.debug("iface_map", extra={"map": self.iface_map})
                # if name == "default":
                #     pass
                # elif name == "serial":
                #     iface["dest_path"] = f"/envds/interface/{iface[]}"

    # async def do_start(self):

    #     try:
    #         await super(Mock1, self).do_start()
    #     except envdsRunTransitionException:
    #         return
            
    #     self.sampling_tasks.append(asyncio.create_task(self.data_loop()))

    # async def do_stop(self):

    #     # do Mock1 specific stop tasks first then call super

    #     try:
    #         await super(Mock1, self).stop()
    #     except envdsRunTransitionException:
    #         return

        # # print("start: 1")
        # super(Mock1, self).start()
        # # print("start: 2")

        # self.data_loop_task.cancel()
        # # print("start: 3")

        # self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRUE)

    # def handle_interface_connect(self, message):
    #     pass

    # def handle_connect(self, message):
    #     pass

    async def handle_interface_message(self, message: Message):
        pass

    async def handle_serial(self, message: Message):
        pass

    async def parse_serial(self, data: CloudEvent):
        pass

    async def data_loop(self):
        # print(f"data_loop:1 - {self.config}")
        # generate mock data at the specified data_rate
        # put on queue for packaging into cloudevent
        # self.logger.info("Starting data_loop", extra=self.extra)
        # print("data_loop:1")
        # print(f"data_rate: {self.data_rate}")
        await asyncio.sleep(time_to_next(self.data_rate))
        # print(f"data_rate: {self.data_rate} ready")
        while True:
            variables = dict()


            dt = get_datetime()
            dt_str = get_datetime_string()
            # print(f"dt: {dt}, {dt_str}")
            # self.config.variables["time"]["data"] = dt_str

            variables["time"] = dt_str

            # variables["latitude"] = round(10 + random.uniform(-1, 1) / 10, 3)
            # variables["longitude"] = round(-150 + random.uniform(-1, 1) / 10, 3)
            # variables["altitude"] = round(100 + random.uniform(-10, 10), 3)

            variables["temperature"] = str(round(25 + random.uniform(-3, 3), 3))
            variables["rh"] = str(round(60 + random.uniform(-5, 5), 3))
            variables["pressure"] = str(round(1000 + random.uniform(-5, 5), 3))
            variables["wind_speed"] = str(round(10 + random.uniform(-5, 5), 3))
            variables["wind_direction"] = str(round(90 + random.uniform(-20, 20), 3))

            # print(f"variables: {variables}")
            # send_meta = False
            # if dt.minute % 10 == 0:
            # # if dt.minute % 1 == 0:
            #     send_meta = True
            # print(f"meta: {send_meta}")
            # record = self.build_data_record(meta=send_meta)
            record = self.build_data_record(meta=self.include_metadata)
            self.include_metadata = False
            # print(f"empty record: {record}")
            for name, val in record["variables"].items():
                # print(name, val)
                if name in variables:
                    instvar = self.config.variables[name]
                    # print(f"instvar: {instvar}")
                    # print(f"type: {instvar.type}, {eval(instvar.type)(variables[name])}")
                    # print(f"name: {name}, val: {val}, instvar: {instvar}")
                    # record["variables"][name]["data"] = eval(self.config.variables[name]["type"])(variables[name])
                    # record["variables"][name]["data"] = eval(instvar.type)(variables[name])
                    val["data"] = eval(instvar.type)(variables[name])
                    # print(f"record: {record}")

            # print(f"data record: {record}")
            src = self.get_id_as_source()
            # print(src)
            event = et.create_data_update(
                # source="sensor.mockco-mock1-1234", data=record
                source=src, data=record
            )
            # print(f"ce: {event.data}")
            # event = et.create_data_update(
            #     source="sensor.mockco-mock1-1234", data={"one":"two"}
            # )
            # event = et.create(type="type", source="source", data={"one": "two"})
            # print(type(event))
            # message=Message(data=event, dest_path="/sensor/mockco/mock1/1234/update")
            # message=Message(data=event, dest_path=f"/{src.replace('.', '/')}/update")
            self.logger.debug("data record event", extra={"data": event})
            message=Message(data=event, dest_path=f"/{self.get_id_as_topic()}/update")
            # print(f"to_json: {event.data}")
            # _, body = to_structured(event)
            # print(f"body: {body}")
            # print(message.dest_path, to_json(message.data).decode())
            await self.send_message(message)

            # data = {
            #     "data": variables,
            #     "instance": {"make": "MockCo", "model": "Sensor-1", "serial": self.sn},
            # }
            # # If we send a message on an even 10-minute mark then
            # # include the metadata packet. This is meant to mock
            # # occasionally updating a station-sensors's metadata
            # if dt.minute % 10 == 0:
            #     data["metadata"] = self.metadata
            #     data["metadata"]["attributes"] = data["instance"]

            # if self.data_buffer:
            #     await self.data_buffer.put(data)

            await asyncio.sleep(time_to_next(self.data_rate))
            # await asyncio.sleep(.1)


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("mock1_test_task", extra={"test": "mock1 task"})


async def shutdown(sensor):
    print("shutting down")
    if sensor:
        await sensor.shutdown()

    for task in task_list:
        print(f"cancel: {task}")
        if task:
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
    logger = logging.getLogger("mockco-mock1")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # print("instantiate")
    logger.debug("Starting Mock1")
    inst = Mock1()
    # print(inst)
    inst.run()
    # print("running")
    # task_list.append(asyncio.create_task(inst.run()))
    # await asyncio.sleep(2)
    inst.start()
    # logger.debug("Starting Mock1")

    # get config from file
    sn = "9999"
    try:
        with open("/app/config/sensor.conf", "r") as f:
            conf = yaml.safe_load(f)
            try:
                sn = conf["serial_number"]
            except KeyError:
                pass
    except FileNotFoundError:
        pass

    root_path=f"/envds/sensor/MockCo/Mock1/{sn}"
    print(f"root_path: {root_path}")

    #TODO: get serial number from config file
    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path=f"/envds/sensor/MockCo/Mock1/{sn}",
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    await server.serve()

    print("starting shutdown...")
    await shutdown(inst)
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
