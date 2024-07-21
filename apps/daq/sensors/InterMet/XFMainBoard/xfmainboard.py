import asyncio
import math
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


class XFMainBoard(Sensor):
    """docstring for XFMainBoard."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "string", "data": "InterMet"},
            "model": {"type": "string", "data": "XFMainBoard"},
            "description": {
                "type": "string",
                "data": "Main hub for sensor data collection",
            },
            "tags": {
                "type": "char",
                "data": "data hub, temperature, rh, humidity",
            },
            "format_version": {"type": "char", "data": "1.0.0"},
            "serial_number": {"type": "string", "data": ""},
        },
        "dimensions": {"time": None},
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "string", "data": "Time"}},
            },
            "press": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pressure"},
                    "units": {"type": "char", "data": "mb"},
                },
            },
            "press_temp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Temperature from pressure sensor"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "rh": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Relative Humidity"},
                    "units": {"type": "char", "data": "%"},
                },
            },
            "rh_temp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Temperature from rh sensor"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
        },
        "settings": {
            # "mcpc_b_yn": {
            #     "type": "int",
            #     "shape": ["time"],
            #     "attributes": {
            #         "long_name": {"type": "char", "data": "MCPC B Present"},
            #         "units": {"type": "char", "data": "count"},
            #         "valid_min": {"type": "int", "data": 0},
            #         "valid_max": {"type": "int", "data": 1},
            #         "step_increment": {"type": "int", "data": 1},
            #         "default_value": {"type": "int", "data": 0},
            #     },
            # },
        },
    }

    def __init__(self, config=None, **kwargs):
        super(XFMainBoard, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_data_buffer = asyncio.Queue()

        # imet sensor id
        self.sensor_id = "0"

        self.enable_task_list.append(self.default_data_loop())
        self.enable_task_list.append(self.sampling_monitor())

        self.collecting = False

    def configure(self):
        super(XFMainBoard, self).configure()

        # get config from file
        try:
            with open("/app/config/sensor.conf", "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            conf = {"serial_number": "UNKNOWN", "interfaces": {}}

        if "metadata_interval" in conf:
            self.include_metadata_interval = conf["metadata_interval"]

        sensor_iface_properties = {
            "default": {
                "sensor-interface-properties": {
                    "connection-properties": {
                        "baudrate": 57600,
                        "bytesize": 8,
                        "parity": "N",
                        "stopbit": 1,
                    },
                    "read-properties": {
                        "read-method": "readline",  # readline, read-until, readbytes, readbinary
                        # "read-terminator": "\r",  # only used for read_until
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
                "hc2a.configure", extra={"interfaces": conf["interfaces"]}
            )

        for name, setting in XFMainBoard.metadata["settings"].items():
            requested = setting["attributes"]["default_value"]["data"]
            if "settings" in config and name in config["settings"]:
                requested = config["settings"][name]

            self.settings.set_setting(name, requested=requested)

        meta = SensorMetadata(
            attributes=XFMainBoard.metadata["attributes"],
            dimensions=XFMainBoard.metadata["dimensions"],
            variables=XFMainBoard.metadata["variables"],
            settings=XFMainBoard.metadata["settings"],
        )

        self.config = SensorConfig(
            make=XFMainBoard.metadata["attributes"]["make"]["data"],
            model=XFMainBoard.metadata["attributes"]["model"]["data"],
            serial_number=conf["serial_number"],
            metadata=meta,
            interfaces=conf["interfaces"],
            daq_id=conf["daq_id"],
        )

        print(f"self.config: {self.config}")

        try:
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
            if "interfaces" in conf:
                for name, iface in conf["interfaces"].items():
                    print(f"add: {name}, {iface}")
                    self.add_interface(name, iface)
                    # self.iface_map[name] = iface
        except Exception as e:
            print(e)

        self.logger.debug("iface_map", extra={"map": self.iface_map})

    async def handle_interface_message(self, message: Message):
        pass

    async def handle_interface_data(self, message: Message):
        await super(XFMainBoard, self).handle_interface_data(message)

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

    async def settings_check(self):
        await super().settings_check()

        if not self.settings.get_health(): # something has changed
            for name in self.settings.get_settings().keys():
                if not self.settings.get_health_setting(name):
                    self.logger.debug("settings_check - set setting", extra={"setting-name": name, "setting": self.settings.get_setting(name)})


    async def sampling_monitor(self):

        # start_command = f"Log,{self.sampling_interval}\n"
        start_command = "msems_mode=2\n"
        stop_command = "msems_mode=0\n"
        need_start = True
        start_requested = False
        # wait to see if data is already streaming
        await asyncio.sleep(2)

        while True:
            try:

                if self.sampling():

                    if need_start:
                        if self.collecting:
                            # await self.interface_send_data(data={"data": stop_command})
                            # if self.polling_task:
                            #     self.polling_task.cancel()
                            await asyncio.sleep(2)
                            self.collecting = False
                            continue
                        else:
                            # await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
                            # self.polling_task = asyncio.create_task(self.polling_loop())
                            need_start = False
                            start_requested = True
                            await asyncio.sleep(2)
                            continue
                    elif start_requested:
                        if self.collecting:
                            start_requested = False
                        else:
                            # await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
                            await asyncio.sleep(2)
                            continue
                else:
                    if self.collecting:
                        # await self.interface_send_data(data={"data": stop_command})
                        # if self.polling_task:
                        #     self.polling_task.cancel()
                        await asyncio.sleep(2)
                        self.collecting = False
                            
                await asyncio.sleep(.1)

                # if self.collecting:
                #     # await self.stop_command()
                #     self.logger.debug("sampling_monitor:5", extra={"self.collecting": self.collecting})
                #     await self.interface_send_data(data={"data": stop_command})
                #     # self.logger.debug("sampling_monitor:6", extra={"self.collecting": self.collecting})
                #     self.collecting = False
                #     # self.logger.debug("sampling_monitor:7", extra={"self.collecting": self.collecting})
            except Exception as e:
                print(f"sampling monitor error: {e}")
                
            await asyncio.sleep(.1)

    async def default_data_loop(self):

        while True:
            try:
                data = await self.default_data_buffer.get()
                # self.collecting = True
                self.logger.debug("default_data_loop", extra={"data": data})
                # continue
                record = self.default_parse(data)
                if record:
                    self.collecting = True

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
            except Exception as e:
                print(f"default_data_loop error: {e}")
            await asyncio.sleep(0.1)

    def default_parse(self, data):
        if data:
            try:
                variables = list(self.config.metadata.variables.keys())
                # print(f"variables: \n{variables}\n{variables2}")
                variables.remove("time")

                record = self.build_data_record(meta=self.include_metadata)
                self.include_metadata = False
 
                try:
                    record["timestamp"] = data.data["timestamp"]
                    record["variables"]["time"]["data"] = data.data["timestamp"]
                    
                    parts = data.data["data"].strip().split(",")
                    # print(f"parts: {parts}, {variables}")
                    if len(parts) == 5 and parts[0] == self.sensor_id:

                        record["variables"]["press"]["data"] = round(float(parts[1])/100.0,2)
                        record["variables"]["press_temp"]["data"] = round(float(parts[2])/100.0,2)
                        record["variables"]["rh"]["data"] = round(float(parts[3])/100.0,2)
                        record["variables"]["rh_temp"]["data"] = round(float(parts[4])/100.0,2)
                        return record

                except (KeyError, ValueError):
                    pass
            except Exception as e:
                print(f"default_parse error: {e}")
        # else:
        return None

class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


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
    logger = logging.getLogger(f"InterMet::XFMainBoard::{sn}")

    logger.debug("Starting imet-XF")
    inst = XFMainBoard()
    # print(inst)
    # await asyncio.sleep(2)
    inst.run()
    # print("running")
    # task_list.append(asyncio.create_task(inst.run()))
    # await asyncio.sleep(2)
    await asyncio.sleep(2)
    inst.start()

    event_loop = asyncio.get_event_loop()
    global do_run
    do_run = True

    def shutdown_handler(*args):
        global do_run
        do_run = False

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    while do_run:
        logger.debug("InterMet.XFMainBoard.run", extra={"do_run": do_run})
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
