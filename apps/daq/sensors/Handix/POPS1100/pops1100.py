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
from envds.core import envdsLogger

# from envds.daq.db import get_sensor_registration, register_sensor  # , envdsBase, envdsStatus
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


class POPS1100(Sensor):
    """docstring for MAGIC250."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "string", "data": "Handix"},
            "model": {"type": "string", "data": "POPS1100"},
            "description": {
                "type": "string",
                "data": "Portable Optical Particle Spectrometer",
            },
            "tags": {
                "type": "char",
                "data": "aerosol, particles, concentration, sensor, sizing, size distribution",
            },
            "format_version": {"type": "char", "data": "1.0.0"},
        },
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "string", "data": "Time"}},
            },
            "POPS_ID": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "string", "data": "POPS ID"}},
            },
            "POPS_DateTime": {
                "type": "str",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "string", "data": "POPS DateTime string"}
                },
            },
            "POPS_DateTime": {
                "type": "str",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "string", "data": "Internal Timestamp"}
                },
            },
            "TimeSSM": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Seconds since midngight"},
                    "units": {"type": "char", "data": "sec"},
                },
            },
            "Status": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Status"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "DataStatus": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Data status"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "PartCt": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Particle counts"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "HistSum": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Sum of particle count histogram"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "PartCon": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Particle concentration"},
                    "units": {"type": "char", "data": "cm-3"},
                },
            },
            "BL": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Current baseline of detector"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "BLTH": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Current threshold for particle counting"},
                    "description": {
                        "type": "char",
                        "data": "Calculated using BL + STD x TH_Mult",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "STD": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Current standard deviation of baseline"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "MaxSTD": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Maximum standard deviation of baseline"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "P": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Ambient pressure measured on POPS Cape"},
                    "units": {"type": "char", "data": "hPa"},
                },
            },
            "TofP": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "On-board temperature measured on POPS Cape"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "PumpLife_hrs": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump Life"},
                    "units": {"type": "char", "data": "hour"},
                },
            },
            "WidthSTD": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Width of standard deviation of baseline"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "AveWidth": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Average of width"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "POPS_Flow": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Current sample flow rate"},
                    "units": {"type": "char", "data": "cm3 s-1"},
                },
            },
            "PumpFB": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump feedback"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "LDTemp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Laser diode board temperature"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "LaserFB": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Laser diode feedback"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "LD_Mon": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Laser diode output power monitor"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "Temp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "External thermistor value"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "BatV": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Battery or input DC power voltage"},
                    "units": {"type": "char", "data": "volt"},
                },
            },
            "Laser_Current": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Laser diode current"},
                    "units": {"type": "char", "data": "count"},
                    # "valid_min": {"type": "float", "data": 0.0},
                    # "valid_max": {"type": "float", "data": 360.0},
                },
            },
            "Flow_Set": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump voltage set point"},
                    "units": {"type": "char", "data": "volt"},
                },
            },
            "BL_Start": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Starting point for baseline value determination",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "TH_Mult": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Threshold multiplier for determining valid particle counts",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "Nbins": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Number of bins for particle raw peak signal distributions",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "Logmin": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Power of 10 for lowest particle signal bin"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "Logmax": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Power of 10 for largest particle signal bin"},
                    "units": {"type": "char", "data": "count"},
                },
            },
            "Skip_save": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Value of the “skip_save” parameter set in configuration file",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "MinPeakPts": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Minimum number of peak points above threshold to be considered valid particle count",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "MaxPeakPts": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Maximum number of peak points above threshold to be considered valid particle count",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "RawPts": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Number of points saved for any raw data recorded",
                    },
                    "units": {"type": "char", "data": "count"},
                },
            },
            "diameter": {
                "type": "float",
                "shape": ["time", "diameter"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Diameter"},
                    "units": {"type": "char", "data": "nm"},
                },
            },
            "diameter_bnd_lower": {
                "type": "float",
                "shape": ["time", "diameter"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Lower bound of bin diameter"},
                    "units": {"type": "char", "data": "nm"},
                },
            },
            "diameter_bnd_upper": {
                "type": "float",
                "shape": ["time", "diameter"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Upper bound of bin diameter"},
                    "units": {"type": "char", "data": "nm"},
                },
            },
            "bin_count": {
                "type": "int",
                "shape": ["time", "diameter"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Raw bin counts for each diameter"},
                    "units": {"type": "char", "data": "nm"},
                },
            },
        },
        "settings": {
            # "pump_power": {
            #     "type": "int",
            #     "shape": ["time"],
            #     "attributes": {
            #         "long_name": {"type": "char", "data": "Pump Power"},
            #         "units": {"type": "char", "data": "count"},
            #         "valid_min": {"type": "int", "data": 0},
            #         "valid_max": {"type": "int", "data": 1},
            #         "step_increment": {"type": "int", "data": 1},
            #         "default_value": {"type": "int", "data": 1},
            #     },
            # },
        },
    }

    def __init__(self, config=None, **kwargs):
        super(POPS1100, self).__init__(config=config, **kwargs)
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_data_buffer = asyncio.Queue()

        self.lower_dp_bound = [
            115.,
            125.,
            135.,
            150.,
            165.,
            185.,
            210.,
            250.,
            350.,
            475.,
            575.,
            855.,
            1220.,
            1530.,
            1990.,
            2585.,
        ]

        self.upper_dp_bound = [
            125.,
            135.,
            150.,
            165.,
            185.,
            210.,
            250.,
            350.,
            475.,
            575.,
            855.,
            1220.,
            1530.,
            1990.,
            2585.,
            3370.,
        ]
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
        # self.enable_task_list.append(self.register_sensor())
        # asyncio.create_task(self.sampling_monitor())
        self.collecting = False

    def configure(self):
        super(POPS1100, self).configure()

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
                        "read-method": "readline",  # readline, read-until, readbytes, readbinary
                        # "read-terminator": "\r",  # only used for read_until
                        "decode-errors": "strict",
                        "send-method": "ascii",
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
                "magcic250.configure", extra={"interfaces": conf["interfaces"]}
            )

        for name, setting in POPS1100.metadata["settings"].items():
            requested = setting["attributes"]["default_value"]["data"]
            if "settings" in config and name in config["settings"]:
                requested = config["settings"][name]

            self.settings.set_setting(name, requested=requested)

        meta = SensorMetadata(
            attributes=POPS1100.metadata["attributes"],
            variables=POPS1100.metadata["variables"],
            settings=POPS1100.metadata["settings"],
        )

        self.config = SensorConfig(
            make=POPS1100.metadata["attributes"]["make"]["data"],
            model=POPS1100.metadata["attributes"]["model"]["data"],
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
        await super(POPS1100, self).handle_interface_data(message)

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

        if not self.settings.get_health():  # something has changed
            for name in self.settings.get_settings().keys():
                if not self.settings.get_health_setting(name):
                    self.logger.debug(
                        "settings_check - set setting",
                        extra={
                            "setting-name": name,
                            "setting": self.settings.get_setting(name),
                        },
                    )

    # async def register_sensor(self):
    #     try:

    #         make = self.config.make
    #         model = self.config.model
    #         serial_number = self.config.serial_number
    #         if not await get_sensor_registration(make=make, model=model, serial_number=serial_number):

    #             await register_sensor(
    #                 make=make,
    #                 model=model,
    #                 serial_number=serial_number,
    #                 source_id=self.get_id_as_source(),
    #             )

    #     except Exception as e:
    #         self.logger.error("sensor_reg error", extra={"e": e})

    async def sampling_monitor(self):


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
                            await asyncio.sleep(2)
                            self.collecting = False
                            continue
                        else:
                            # await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
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
                        await asyncio.sleep(2)
                        self.collecting = False

                await asyncio.sleep(0.1)

                # if self.collecting:
                #     # await self.stop_command()
                #     self.logger.debug("sampling_monitor:5", extra={"self.collecting": self.collecting})
                #     await self.interface_send_data(data={"data": stop_command})
                #     # self.logger.debug("sampling_monitor:6", extra={"self.collecting": self.collecting})
                #     self.collecting = False
                #     # self.logger.debug("sampling_monitor:7", extra={"self.collecting": self.collecting})
            except Exception as e:
                print(f"sampling monitor error: {e}")

            await asyncio.sleep(0.1)

    # async def start_command(self):
    #     pass # Log,{sampling interval}

    # async def stop_command(self):
    #     pass # Log,0

    # def stop(self):
    #     asyncio.create_task(self.stop_sampling())
    #     super().start()

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

                # print(record)
                # print(self.sampling())
                if record and self.sampling():

                    # add diameters
                    record["variables"]["diameter_bnd_lower"]["data"] = self.lower_dp_bound
                    record["variables"]["diameter_bnd_upper"]["data"] = self.upper_dp_bound
                    diams = []
                    for lower,upper in zip(self.lower_dp_bound, self.upper_dp_bound):
                        diams.append(round(math.sqrt(lower*upper)), 1)
                    record["variables"]["diameter"]["data"] = diams

                    event = DAQEvent.create_data_update(
                        # source="sensor.mockco-mock1-1234", data=record
                        source=self.get_id_as_source(),
                        data=record,
                    )
                    dest_path = f"/{self.get_id_as_topic()}/data/update"
                    self.logger.debug(
                        "default_data_loop",
                        extra={"data": event, "dest_path": dest_path},
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
                variables.remove("diameter")
                variables.remove("diameter_bnd_lower")
                variables.remove("diameter_bnd_upper")
                # variables2.remove("time")
                # print(f"variables: \n{variables}\n{variables2}")

                # print(f"include metadata: {self.include_metadata}")
                record = self.build_data_record(meta=self.include_metadata)
                # print(f"default_parse: data: {data}, record: {record}")
                self.include_metadata = False
                try:
                    record["timestamp"] = data.data["timestamp"]
                    record["variables"]["time"]["data"] = data.data["timestamp"]
                    parts = data.data["data"].strip().split(",")

                    # remove first parameter ("POPS") from data line as it's not used
                    parts.pop(0)

                    # print(f"parts: {parts}, {variables}")
                    dist_index = None
                    
                    if len(parts) < 37:
                        return None
                    for index, name in enumerate(variables):
                        if name in record["variables"]:
                            # instvar = self.config.variables[name]

                            if name == "bin_count":
                                dist_index = index
                                break

                            instvar = self.config.metadata.variables[name]
                            vartype = instvar.type
                            if instvar.type == "string":
                                vartype = "str"
                            try:
                                # print(f"default_parse: {record['variables'][name]} - {parts[index].strip()}")
                                record["variables"][name]["data"] = eval(vartype)(
                                    parts[index].strip()
                                )
                            except ValueError:
                                if vartype == "str" or vartype == "char":
                                    record["variables"][name]["data"] = ""
                                else:
                                    record["variables"][name]["data"] = None
                    
                    # get distribution
                    bin_counts = []
                    for val in parts[index:]:
                        bin_counts.append(int(val.strip()))
                    record["variables"]["bin_count"]["data"] = bin_counts

                    return record
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
    logger = logging.getLogger(f"Handix::POPS1100::{sn}")

    logger.debug("Starting POPS1100")
    inst = POPS1100()
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
        logger.debug("POPS1100.run", extra={"do_run": do_run})
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
