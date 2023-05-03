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
import random
from envds.core import envdsLogger  # , envdsBase, envdsStatus
from envds.util.util import (
    # get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)
from envds.daq.sensor import Sensor, SensorConfig, SensorVariable, SensorMetadata

# from envds.event.event import create_data_update, create_status_update
from envds.daq.types import DAQEventType as det
from envds.daq.event import DAQEvent
from envds.message.message import Message

# from envds.exceptions import envdsRunTransitionException

# from typing import Union
# from cloudevents.http import CloudEvent, from_dict, from_json
# from cloudevents.conversion import to_json, to_structured

from pydantic import BaseModel

# from envds.daq.db import init_sensor_type_registration, register_sensor_type

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
            "format_version": {"type": "char", "data": "1.0.0"},
        },
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "char", "data": "Time"}},
            },
            "temperature": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Temperature"},
                    "units": {"type": "char", "data": "degree_C"},
                },
            },
            "rh": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "RH"},
                    "units": {"type": "char", "data": "percent"},
                },
            },
            "pressure": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pressure"},
                    "units": {"type": "char", "data": "hPa"},
                },
            },
            "wind_speed": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Wind Speed"},
                    "units": {"type": "char", "data": "m s-1"},
                },
            },
            "wind_direction": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Wind Direction"},
                    "units": {"type": "char", "data": "degree"},
                    "valid_min": {"type": "float", "data": 0.0},
                    "valid_max": {"type": "float", "data": 360.0},
                },
            },
            "flow_rate": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Flow Rate"},
                    "units": {"type": "char", "data": "l min-1"},
                    "valid_min": {"type": "float", "data": 0.0},
                    "valid_max": {"type": "float", "data": 5.0},
                },
            },
        },
        "settings": {
            "flow_rate": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Flow Rate"},
                    "units": {"type": "char", "data": "l min-1"},
                    "valid_min": {"type": "float", "data": 0.0},
                    "valid_max": {"type": "float", "data": 5.0},
                },
            },
        },
    }

    def __init__(self, config=None, **kwargs):
        super(Mock1, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_data_buffer = asyncio.Queue()

        # os.environ["REDIS_OM_URL"] = "redis://redis.default"

        # self.data_loop_task = None

        # all handled in run_setup ----
        # self.configure()

        # # self.logger = logging.getLogger(f"{self.config.make}-{self.config.model}-{self.config.serial_number}")
        # self.logger = logging.getLogger(self.build_app_uid())

        # # self.update_id("app_uid", f"{self.config.make}-{self.config.model}-{self.config.serial_number}")
        # self.update_id("app_uid", self.build_app_uid())

        # self.logger.debug("id", extra={"self.id": self.id})
        # print(f"config: {self.config}")
        # ----

        # self.sampling_task_list.append(self.data_loop())
        self.enable_task_list.append(self.default_data_loop())
        self.enable_task_list.append(self.test_polling_loop())

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

        # # create SensorConfig
        # var_list = []
        # var_map = dict()
        # for name, val in Mock1.metadata["variables"].items():
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

        # atts = Mock1.metadata["attributes"]
        # self.config = SensorConfig(
        #     make=atts["make"]["data"],
        #     model=atts["model"]["data"],
        #     serial_number=conf["serial_number"],
        #     variables=var_map,
        #     interfaces=conf["interfaces"],
        #     daq_id=conf["daq_id"],
        # )

        # TODO: add info to interface config (e.g., connection properties, read_method, etc)
        sensor_iface_properties = {
            "default": {
                "sensor-interface-properties": {
                    "connection-properties": {
                        "baudrate": 9600,
                        "bytesize": 8,
                        "parity": "N",
                        "stopbit": 1,
                    },
                    "read-properties": {
                        "read-method": "readline",  # readline, read-until, readbytes, readbinary
                        "read-terminator": "\r",  # only used for read_until
                        "decode-errors": "strict",
                        "send-method": "ascii"
                    },
                }
            }
        }

        if "interfaces" in conf:
            for name, iface in conf["interfaces"].items():
                if name in sensor_iface_properties:
                    for propname, prop in sensor_iface_properties[name].items():
                        iface[propname] = prop

            self.logger.debug(
                "mock1.configure", extra={"interfaces": conf["interfaces"]}
            )

        meta = SensorMetadata(
            attributes=Mock1.metadata["attributes"],
            variables=Mock1.metadata["variables"],
            settings=Mock1.metadata["settings"],
        )

        self.config = SensorConfig(
            make=Mock1.metadata["attributes"]["make"]["data"],
            model=Mock1.metadata["attributes"]["model"]["data"],
            serial_number=conf["serial_number"],
            metadata=meta,
            interfaces=conf["interfaces"],
            daq_id=conf["daq_id"],
        )

        print(f"self.config: {self.config}")

        try:
            # self.sensor_format_version = atts["format_version"]
            self.sensor_format_version = self.config.metadata.attributes[
                "format_version"
            ].data
        except KeyError:
            pass

        self.logger.debug(
            "configure",
            extra={"conf": conf, "self.config": self.config},
        )

        try:

            # for name, iface in self.config.interfaces.items():
            #     # for name, iface in conf.items():
            #     print(f"add: {name}, {iface}")
            #     self.add_interface(name, iface)

            if "interfaces" in conf:
                for name, iface in conf["interfaces"].items():
                    print(f"add: {name}, {iface}")
                    self.add_interface(name, iface)
                    # self.iface_map[name] = iface
        except Exception as e:
            print(e)

        self.logger.debug("iface_map", extra={"map": self.iface_map})
        # if name == "default":
        #     pass
        # elif name == "serial":
        #     iface["dest_path"] = f"/envds/interface/{iface[]}"

    # def run_setup(self):
    #     super().run_setup()
    #     asyncio.create_task(self.register_sensor_type())

    # async def register_sensor_type(self):
    #     await init_sensor_type_registration()
    #     await register_sensor_type(
    #         make=self.get_make(), model=self.get_model(), metadata=self.get_metadata()
    #     )

    async def handle_interface_message(self, message: Message):
        pass

    # async def handle_serial(self, message: Message):
    #     pass

    # async def parse_serial(self, data: CloudEvent):
    # pass

    async def handle_interface_data(self, message: Message):
        await super(Mock1, self).handle_interface_data(message)

        # self.logger.debug("interface_recv_data", extra={"data": message.data})
        if message.data["type"] == det.interface_data_recv():
            try:
                path_id = message.data["path_id"]
                iface_path = self.config.interfaces["default"]["path"]
                # if path_id == "default":
                if path_id == iface_path:
                    self.logger.debug(
                        "interface_recv_data", extra={"data": message.data.data}
                    )
                    await self.default_data_buffer.put(message.data)
            except KeyError:
                pass
    
    async def test_polling_loop(self):
        while True:
            poll_cmd = "read\n"
            await self.interface_send_data(data={"data": poll_cmd})
            await asyncio.sleep(1)


    async def default_data_loop(self):

        while True:
            data = await self.default_data_buffer.get()
            # self.logger.debug("default_data_loop", extra={"data": data})
            record = self.default_parse(data)

            # print(record)
            # print(self.sampling())
            if record and self.sampling():
                event = DAQEvent.create_data_update(
                    # source="sensor.mockco-mock1-1234", data=record
                    source=self.get_id_as_source(),
                    data=record,
                )
                dest_path = f"/{self.get_id_as_topic()}/data/update"
                self.logger.debug(
                    "default_data_loop", extra={"data": event, "dest_path": dest_path}
                )
                message = Message(data=event, dest_path=dest_path)
                # self.logger.debug("default_data_loop", extra={"m": message})
                await self.send_message(message)

            # self.logger.debug("default_data_loop", extra={"record": record})
            await asyncio.sleep(0.1)

    def default_parse(self, data):
        if data:

            # variables = [
            #     "time",
            #     "temperature",
            #     "rh",
            #     "pressure",
            #     "wind_speed",
            #     "wind_direction",
            # ]
            # variables = list(self.config.variables.keys())
            variables = list(self.config.metadata.variables.keys())
            # print(f"variables: \n{variables}\n{variables2}")
            variables.remove("time")
            # variables2.remove("time")
            # print(f"variables: \n{variables}\n{variables2}")

            # print(f"include metadata: {self.include_metadata}")
            record = self.build_data_record(meta=self.include_metadata)
            self.include_metadata = False
            try:
                record["timestamp"] = data.data["timestamp"]
                record["variables"]["time"]["data"] = data.data["timestamp"]
                parts = data.data["data"].split(",")
                for index, name in enumerate(variables):
                    if name in record["variables"]:
                        # instvar = self.config.variables[name]
                        instvar = self.config.metadata.variables[name]
                        record["variables"][name]["data"] = eval(instvar.type)(
                            parts[index]
                        )
                return record
            except KeyError:
                pass
        # else:
        return None

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
            variables["flow_rate"] = str(round(2 + random.uniform(-0.1, 0.1), 3))

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
                    instvar = self.config.metadata.variables[name]
                    # print(f"instvar: {instvar}")
                    # print(f"type: {instvar.type}, {eval(instvar.type)(variables[name])}")
                    # print(f"name: {name}, val: {val}, instvar: {instvar}")
                    # record["variables"][name]["data"] = eval(self.config.variables[name]["type"])(variables[name])
                    # record["variables"][name]["data"] = eval(instvar.type)(variables[name])
                    val["data"] = eval(instvar.type)(variables[name])
                    # print(f"record: {record}")

            print(f"data record: {record}")
            src = self.get_id_as_source()
            # print(src)
            event = DAQEvent.create_data_update(
                # source="sensor.mockco-mock1-1234", data=record
                source=src,
                data=record,
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
            message = Message(data=event, dest_path=f"/{self.get_id_as_topic()}/update")
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

    # def start(self):
    #     super().start()
    #     self.logger.debug("mock1.start", extra={"status": self.status.get_status()})


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

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger(f"mockco::mock1::{sn}")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # print("instantiate")
    logger.debug("Starting Mock1")
    inst = Mock1()
    # print(inst)
    # await asyncio.sleep(2)
    inst.run()
    # print("running")
    # task_list.append(asyncio.create_task(inst.run()))
    # await asyncio.sleep(2)
    inst.start()
    # logger.debug("Starting Mock1")

    # remove fastapi ----
    # root_path = f"/envds/sensor/MockCo/Mock1/{sn}"
    # # print(f"root_path: {root_path}")

    # # TODO: get serial number from config file
    # config = uvicorn.Config(
    #     "main:app",
    #     host=server_config.host,
    #     port=server_config.port,
    #     log_level=server_config.log_level,
    #     root_path=f"/envds/sensor/MockCo/Mock1/{sn}",
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
        logger.debug("mock1.run", extra={"do_run": do_run})
        await asyncio.sleep(1)

    logger.info("starting shutdown...")
    await shutdown(inst)
    logger.info("done.")


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
