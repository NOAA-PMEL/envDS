import asyncio
import math
import signal
import struct

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


class STAP9406(Sensor):
    """docstring for STAP9406."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "string", "data": "Brechtel"},
            "model": {"type": "string", "data": "STAP9406"},
            "description": {
                "type": "string",
                "data": "Miniaturized single channel, tri-color absoprtion photomter",
            },
            "tags": {
                "type": "char",
                "data": "aerosol, particles, absorption",
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
            "invmm_r": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Absorption coefficent, red"},
                    "units": {"type": "char", "data": "Mm-1"},
                },
            },
            "invmm_g": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Absorption coefficent, green"},
                    "units": {"type": "char", "data": "Mm-1"},
                },
            },
            "invmm_b": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Absorption coefficent, blue"},
                    "units": {"type": "char", "data": "Mm-1"},
                },
            },
            "red_smp": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, red sample"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "red_ref": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, red reference"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "grn_smp": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, green sample"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "grn_ref": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, green reference"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "blu_smp": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, blue sample"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "blu_ref": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw intensity, blue reference"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "blk_smp": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Black intensity, sample"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "blk_ref": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Black intensity, reference"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "smp_flw": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sample flow"},
                    "units": {"type": "char", "data": "l min-1"},
                },
            },
            "smp_tmp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sample temperature"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "smp_prs": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sample pressure"},
                    "units": {"type": "char", "data": "mb"},
                },
            },
            "pump_pw": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump power"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "psvolts": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Power supply input volts"},
                    "units": {"type": "char", "data": "volts"},
                },
            },
            "cntdown": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Countdown timer"},
                    "units": {"type": "char", "data": "sec"},
                },
            },
            "sd_stat": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Save to disk state"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "fltstat": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Filter state"},
                    "units": {"type": "char", "data": "count"},
                },
            },
        },
        "settings": {
            "stapctl": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Stap control state (0=off, 1=on)"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 1},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 1},
                },
            },
            "sd_save": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Save to sd card (0=off, 1=on)"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 1},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 0},
                },
            },
            "flt_typ": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Filter type (0=Pall, 1=EMFAB, Azumi, 2=Azumi)"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 2},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 2},
                },
            },
            "fltstat": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sets filter status, used for filter initialization (see manual for details)"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 7},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 0},
                },
            },
            "flow_sp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Flow set point"},
                    "units": {"type": "char", "data": "l min-1"},
                    "valid_min": {"type": "float", "data": 0.5},
                    "valid_max": {"type": "float", "data": 2.0},
                    "step_increment": {"type": "float", "data": 0.5},
                    "default_value": {"type": "float", "data": 1.0},
                },
            },
            "intrvl": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sample averaging interval"},
                    "units": {"type": "char", "data": "sec"},
                    "valid_min": {"type": "int", "data": 1},
                    "valid_max": {"type": "int", "data": 60},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 60},
                },
            },
        },
    }

    def __init__(self, config=None, **kwargs):
        super(STAP9406, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_data_buffer = asyncio.Queue()

        self.scan_state = None
        self.reading_scan = False
        self.scan_ready = False
        self.current_record = None
        self.started_record = False
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
        self.enable_task_list.append(self.sampling_monitor())
        # asyncio.create_task(self.sampling_monitor())
        self.collecting = False

    def configure(self):
        super(STAP9406, self).configure()

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
                        "baudrate": 115200,
                        "bytesize": 8,
                        "parity": "N",
                        "stopbit": 1,
                    },
                    "read-properties": {
                        "read-method": "readuntil",  # readline, read-until, readbytes, readbinary
                        "read-terminator": "\r",  # only used for read_until
                        # "decode-errors": "strict",
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
                "msems2404.configure", extra={"interfaces": conf["interfaces"]}
            )

        for name, setting in STAP9406.metadata["settings"].items():
            requested = setting["attributes"]["default_value"]["data"]
            if "settings" in config and name in config["settings"]:
                requested = config["settings"][name]

            self.settings.set_setting(name, requested=requested)

        meta = SensorMetadata(
            attributes=STAP9406.metadata["attributes"],
            dimensions=STAP9406.metadata["dimensions"],
            variables=STAP9406.metadata["variables"],
            settings=STAP9406.metadata["settings"],
        )

        self.config = SensorConfig(
            make=STAP9406.metadata["attributes"]["make"]["data"],
            model=STAP9406.metadata["attributes"]["model"]["data"],
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
        await super(STAP9406, self).handle_interface_data(message)

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
                    await self.set_settings(name)


    async def set_settings(self, name: str):
        setting = self.settings.get_setting(name)
        if setting:
            # if name == "new_pos":
            requested = setting["requested"]
            # in non-mock, send command to set the proper parameter
            if name == "flow_sp":
                requested = float(requested)
                print(f"flow_sp: {name}, {requested}")
                val = hex(int(requested*100))
                val = struct.pack(">I", (int(requested*100)))
                print(f"flow_sp: {val}")
                await self.interface_send_data(data={"data": f"{name}={val}\r"})
            # elif name == "fltstat":
            #     requested = float(requested)
            #     print(f"fltstat: {name}, {requested}")
            #     val = hex(int(requested))
            #     # val = struct.pack(">i", (int(requested)))
            #     print(f"fltstat: {val}")
            #     await self.interface_send_data(data={"data": f"{name}={val}\r"})
            else:
                # in non-mock, send command to set the proper parameter
                await self.interface_send_data(data={"data": f"{name}={requested}\r"})
            # await self.interface_send_data(data={"data": f"{name}={requested}\r"})
            
            self.settings.set_setting(name, actual=requested, requested=requested)


    async def sampling_monitor(self):

        # start_command = f"Log,{self.sampling_interval}\n"
        # start_command = "msems_mode=2\n"
        # stop_command = "msems_mode=0\n"
        need_start = True
        start_requested = False
        # wait to see if data is already streaming
        await asyncio.sleep(2)
        # # if self.collecting:
        # await self.interface_send_data(data={"data": stop_command})
        # await asyncio.sleep(2)
        # self.collecting = False
        # init to stopped
        # await self.stop_command()

        while True:
            try:
                # self.logger.debug("sampling_monitor", extra={"self.collecting": self.collecting})
                # while self.sampling():
                #     # self.logger.debug("sampling_monitor:1", extra={"self.collecting": self.collecting})
                #     if not self.collecting:
                #         # await self.start_command()
                #         self.logger.debug("sampling_monitor:2", extra={"self.collecting": self.collecting})
                #         await self.interface_send_data(data={"data": start_command})
                #         await asyncio.sleep(1)
                #         # self.logger.debug("sampling_monitor:3", extra={"self.collecting": self.collecting})
                #         self.collecting = True
                #         # self.logger.debug("sampling_monitor:4", extra={"self.collecting": self.collecting})

                if self.sampling():

                    if need_start:
                        if self.collecting:
                            # await self.interface_send_data(data={"data": stop_command})
                            if self.polling_task:
                                self.polling_task.cancel()
                            await asyncio.sleep(2)
                            self.collecting = False
                            continue
                        else:
                            # await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
                            self.polling_task = asyncio.create_task(self.polling_loop())
                            need_start = False
                            start_requested = True
                            await asyncio.sleep(2)
                            continue
                    elif start_requested:
                        if self.collecting:
                            start_requested = False
                        else:
                            if not self.polling_task:
                                self.polling_task = asyncio.create_task(self.polling_loop())
                            # await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
                            await asyncio.sleep(2)
                            continue
                else:
                    if self.collecting:
                        # await self.interface_send_data(data={"data": stop_command})
                        if self.polling_task:
                            self.polling_task.cancel()
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


    # async def start_command(self):
    #     pass # Log,{sampling interval}

    # async def stop_command(self):
    #     pass # Log,0

    # def stop(self):
    #     asyncio.create_task(self.stop_sampling())
    #     super().start()
    async def polling_loop(self):

        poll_cmd = 'read\r'
        while True:
            try:
                self.logger.debug("polling_loop", extra={"poll_cmd": poll_cmd})
                await self.interface_send_data(data={"data": poll_cmd})
                await asyncio.sleep(time_to_next(self.data_rate/2.))
            except Exception as e:
                self.logger.error("polling_loop", extra={"e": e})


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

                    # # print(record)
                    # # print(self.sampling())
                    # if self.scan_ready and self.current_record and self.sampling():

                    #     # calc diameters
                    #     # try:
                    #     #     min_dp = self.config... self.current_run_settings["min_diameter_sp"]
                    #     # except KeyError:
                    #     #     min_dp = 10
                    #     min_dp = 10

                    #     try:
                    #         max_dp = self.current_record["actual max dia"]["data"]
                    #     except KeyError:
                    #         max_dp = 300

                    #     dlogdp = math.pow(10, math.log10(max_dp / min_dp) / (30 - 1))
                    #     # dlogdp = dlogdp / (30-1)
                    #     diam = []
                    #     # diam_um = []
                    #     diam.append(10)
                    #     # diam_um.append(10 / 1000)
                    #     for x in range(1, 30):
                    #         dp = round(diam[x - 1] * dlogdp, 2)
                    #         diam.append(dp)
                    #         # diam_um.append(round(dp / 1000, 3))

                    #     self.current_record["actual max dia"]["data"] = diam

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
                    self.started_record = False

                # self.logger.debug("default_data_loop", extra={"record": record})
            except Exception as e:
                print(f"default_data_loop error: {e}")
            await asyncio.sleep(0.1)

    def default_parse(self, data):
        if data:
            try:
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
                # record = self.build_data_record(meta=self.include_metadata)
                # # print(f"default_parse: data: {data}, record: {record}")
                # self.include_metadata = False
                try:

                    # record["timestamp"] = data.data["timestamp"]
                    # record["variables"]["time"]["data"] = data.data["timestamp"]

                    # self.record_ready = False

                    line = data.data["data"].rstrip()#.split()
                    print(f"***line: {line}")
                    if "=" in line:
                        parts = line.split("=")
                    else:
                        return None
                    if len(parts) < 2:
                        return None

                    name = parts[0]
                    value = parts[1]
                    # print(f"name, value: {name}, {value}")
                    if name == "invmm_r":
                        # self.scan_state = parts[1]
                        self.current_record = self.build_data_record(meta=self.include_metadata)
                        self.current_record["timestamp"] = data.data["timestamp"]
                        self.current_record["variables"]["time"]["data"] = data.data["timestamp"]
                        self.include_metadata = False
                        self.started_record = True

                    if self.started_record:
                        if name in self.current_record["variables"]:
                            instvar = self.config.metadata.variables[name]
                            vartype = instvar.type
                            if instvar.type == "string":
                                vartype = "str"
                            try:
                                # print(f"default_parse: {record['variables'][name]} - {parts[index].strip()}")
                                self.current_record["variables"][name]["data"] = eval(vartype)(
                                    value.strip()
                                )
                            except ValueError:
                                if vartype == "str" or vartype == "char":
                                    self.current_record["variables"][name]["data"] = ""
                                else:
                                    self.current_record["variables"][name]["data"] = None

                    if self.started_record and name == 'fltstat':
                        self.started_record = False
                        print(f"done with scan: {self.current_record}")
                        return self.current_record

                    return None
                except KeyError:
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
    logger = logging.getLogger(f"Brechtel::mSEMS9404::{sn}")

    logger.debug("Starting mSEMS9404")
    inst = STAP9406()
    # print(inst)
    # await asyncio.sleep(2)
    inst.run()
    # print("running")
    # task_list.append(asyncio.create_task(inst.run()))
    # await asyncio.sleep(2)
    await asyncio.sleep(2)
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
