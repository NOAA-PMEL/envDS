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
            "format_version": {"type": "char", "data": "1.0.0"},
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
            "serial_number": {
                "type": "string",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Serial Number",
                    },
                },
            },
        },
        "settings": {
            "pump_power": {
                "type": "int",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Pump Power"},
                    "units": {"type": "char", "data": "count"},
                    "valid_min": {"type": "int", "data": 0},
                    "valid_max": {"type": "int", "data": 1},
                    "step_increment": {"type": "int", "data": 1},
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
                },
            },
        },
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

    async def sampling_monitor(self):

        collecting = False
        # init to stopped
        # await self.stop_command()

        start_command = f"Log,{self.sampling_interval}\n"
        stop_command = "Log,0\n"
        while True:
            
            while self.sampling():
                if not collecting:
                    # await self.start_command()
                    await self.interface_send_data(data={"data": start_command})
                    collecting = True

            if collecting:
                # await self.stop_command()
                await self.interface_send_data(data={"data": stop_command})
                collecting = False

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
                        vartype = instvar.type
                        if instvar.type == "string":
                            vartype = "str"
                        try:
                            record["variables"][name]["data"] = eval(instvar.type)(
                                parts[index]
                            )
                        except ValueError:
                            if vartype == "str" or vartype == "char":
                                record["variables"][name]["data"] = ""
                            else:
                                record["variables"][name]["data"] = None
                return record
            except KeyError:
                pass
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
