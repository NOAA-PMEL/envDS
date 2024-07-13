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


class MAGIC250(Sensor):
    """docstring for MAGIC250."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "make": {"type": "string", "data": "AerosolDynamics"},
            "model": {"type": "string", "data": "MAGIC250"},
            "description": {
                "type": "string",
                "data": "Water based Condensation Particle Counter (CPC) manufactured by Aerosol Dyanamics and distributed by Aerosol Devices/Handix",
            },
            "tags": {
                "type": "char",
                "data": "aerosol, cpc, particles, concentration, sensor",
            },
            "format_version": {"type": "char", "data": "2.0.0"},
            "format_version_changes": {"type": "string", "data": "1.0.0 to 2.0.0: moved settings into varialbes and add attribute 'variable_type': 'settings'"}
        },
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "string", "data": "Time"}},
            },
            "magic_timestamp": {
                "type": "str",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "string", "data": "Internal Timestamp"}
                },
            },
            "concentration": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Concentration"},
                    "units": {"type": "char", "data": "cm-3"},
                },
            },
            "dew_point": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Dew Point"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "input_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Input T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "input_rh": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Input RH"},
                    "units": {"type": "char", "data": "percent"},
                },
            },
            "cond_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Conditioner T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "init_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Initiator T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "mod_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Moderator T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "opt_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Optics Head T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "heatsink_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Heat Sink T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "case_T": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Case T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "wick_sensor": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Wick Sensor"},
                    "units": {"type": "char", "data": "percent"},
                },
            },
            "mod_T_sp": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Moderator Set Point T"},
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "humid_exit_dew_point": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Humidifier Exit Dew Point (estimated)",
                    },
                    "units": {"type": "char", "data": "degrees_C"},
                },
            },
            "abs_pressure": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Absolute Pressure"},
                    "units": {"type": "char", "data": "mbar"},
                },
            },
            "flow": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Volumetric Flow Rate"},
                    "units": {"type": "char", "data": "cm3 min-1"},
                    # "valid_min": {"type": "float", "data": 0.0},
                    # "valid_max": {"type": "float", "data": 5.0},
                },
            },
            "log_interval": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Logging Interval"},
                    "units": {"type": "char", "data": "seconds"},
                },
            },
            "corr_live_time": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Corrected Live Time"},
                    "description": {
                        "type": "char",
                        "data": "Live Time as a fraction of interval, x10000, corrected for coincidence",
                    },
                    "units": {"type": "char", "data": "count"},
                    # "valid_min": {"type": "float", "data": 0.0},
                    # "valid_max": {"type": "float", "data": 360.0},
                },
            },
            "meas_dead_time": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Measured Dead Time"},
                    "description": {
                        "type": "char",
                        "data": "Dead Time as a fraction of interval, x10000, raw measurement",
                    },
                    "units": {"type": "char", "data": "count"},
                    # "valid_min": {"type": "float", "data": 0.0},
                    # "valid_max": {"type": "float", "data": 360.0},
                },
            },
            "raw_counts": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Raw Counts during logging interval",
                    },
                    "units": {"type": "char", "data": "count"},
                    # "valid_min": {"type": "float", "data": 0.0},
                    # "valid_max": {"type": "float", "data": 360.0},
                },
            },
            "dthr2_pctl": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Upper Threshold.Percentile"},
                    "description": {
                        "type": "char",
                        "data": "Two pieces of information. The number before the decimal is the upper threshold in mV. The number after the decimal represents the percentage of light-scattering pulses that were large enough to exceed the upper threshold. Under default settings dhtr2 represents the median puls height.",
                    },
                },
            },
            "status_hex": {
                "type": "string",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Compact display of status codes",
                    },
                },
            },
            "status_ascii": {
                "type": "string",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Alphabetic list of all abnormal status codes",
                    },
                },
            },
            "magic_serial_number": {
                "type": "string",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Serial Number",
                    },
                },
            },
            "pump_power": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump Power"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 1},
                    "step_increment": {"type": "int", "data": 1},
                    "default_value": {"type": "int", "data": 1},
                    "variable_type": "settings",
                },
            },
            "q_target": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Target Volumetric Flow Rate"},
                    "units": {"type": "char", "data": "cm3 min-1"},
                    "valid_min": {"type": "int", "data": 240},
                    "valid_max": {"type": "int", "data": 360},
                    "step_increment": {"type": "int", "data": 10},
                    "default_value": {"type": "int", "data": 300},
                    "variable_type": "settings",
                },
            },
        },
        # "settings": {
        #     "pump_power": {
        #         "type": "int",
        #         "shape": ["time"],
        #         "attributes": {
        #             "long_name": {"type": "char", "data": "Pump Power"},
        #             "units": {"type": "char", "data": "count"},
        #             "valid_min": {"type": "int", "data": 0},
        #             "valid_max": {"type": "int", "data": 1},
        #             "step_increment": {"type": "int", "data": 1},
        #             "default_value": {"type": "int", "data": 1},
        #         },
        #     },
        #     "q_target": {
        #         "type": "int",
        #         "shape": ["time"],
        #         "attributes": {
        #             "long_name": {"type": "char", "data": "Target Volumetric Flow Rate"},
        #             "units": {"type": "char", "data": "cm3 min-1"},
        #             "valid_min": {"type": "int", "data": 240},
        #             "valid_max": {"type": "int", "data": 360},
        #             "step_increment": {"type": "int", "data": 10},
        #             "default_value": {"type": "int", "data": 300},
        #         },
        #     },
        # },
    }

    def __init__(self, config=None, **kwargs):
        super(MAGIC250, self).__init__(config=config, **kwargs)
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
        self.enable_task_list.append(self.sampling_monitor())
        # self.enable_task_list.append(self.register_sensor())
        # asyncio.create_task(self.sampling_monitor())
        self.collecting = False

    def configure(self):
        super(MAGIC250, self).configure()

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
                "magcic250.configure", extra={"interfaces": conf["interfaces"]}
            )

        for name, setting in MAGIC250.metadata["settings"].items():
            requested = setting["attributes"]["default_value"]["data"]
            if "settings" in config and name in config["settings"]:
                requested = config["settings"][name]

            self.settings.set_setting(name, requested=requested)

        meta = SensorMetadata(
            attributes=MAGIC250.metadata["attributes"],
            variables=MAGIC250.metadata["variables"],
            settings=MAGIC250.metadata["settings"],
        )

        self.config = SensorConfig(
            make=MAGIC250.metadata["attributes"]["make"]["data"],
            model=MAGIC250.metadata["attributes"]["model"]["data"],
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
        await super(MAGIC250, self).handle_interface_data(message)

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

        # start_command = f"Log,{self.sampling_interval}\n"
        start_command = "Log,1\n"
        stop_command = "Log,0\n"

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
                            await self.interface_send_data(data={"data": stop_command})
                            await asyncio.sleep(2)
                            self.collecting = False
                            continue
                        else:
                            await self.interface_send_data(data={"data": start_command})
                        # await self.interface_send_data(data={"data": "\n"})
                            need_start = False
                            start_requested = True
                            await asyncio.sleep(2)
                            continue
                    elif start_requested:
                        if self.collecting:
                            start_requested = False
                        else:
                            await self.interface_send_data(data={"data": start_command})
                            # await self.interface_send_data(data={"data": "\n"})
                            await asyncio.sleep(2)
                            continue
                else:
                    if self.collecting:
                        await self.interface_send_data(data={"data": stop_command})
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
                # print(f"default_parse: data: {data}, record: {record}")
                self.include_metadata = False
                try:
                    record["timestamp"] = data.data["timestamp"]
                    record["variables"]["time"]["data"] = data.data["timestamp"]
                    parts = data.data["data"].split(",")
                    # print(f"parts: {parts}, {variables}")
                    if len(parts) < 10:
                        return None
                    for index, name in enumerate(variables):
                        if name in record["variables"]:
                            # instvar = self.config.variables[name]
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
    logger = logging.getLogger(f"AerosolDynamics::MAGIC250::{sn}")

    logger.debug("Starting MAGIC250")
    inst = MAGIC250()
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
