import asyncio
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import sys
import os
import json
import logging
from logfmter import Logfmter
import logging.config
from pydantic import BaseSettings, Field
from envds.core import envdsBase, envdsLogger
from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
    datetime_to_string,
    string_to_datetime,
)

# import redis.asyncio as redis
# from redis.commands.json.path import Path
from ulid import ULID

# from envds.message.message import Message
from envds.message.message import Message
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured
from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as bet
from envds.daq.types import DAQEventType as det
from envds.daq.event import DAQEvent


from envds.daq.sensor import Sensor
from envds.daq.db import (
    SensorTypeRegistration,
    SensorRegistration,
    init_db_models,
    register_sensor_type,
    register_sensor,
    get_sensor_type_registration,
    get_sensor_registration,
    get_all_sensor_registration,
    get_sensor_registration_by_pk,
    get_all_sensor_type_registration,
    get_sensor_type_registration_by_pk,
    get_sensor_type_metadata,
)

from aredis_om import (
    # EmbeddedJsonModel,
    # JsonModel,
    # Field,
    # Migrator,
    # # get_redis_connection,
    NotFoundError,
)

# from envds.daq.registration import (
#     init_sensor_registration,
#     register_sensor,
#     get_sensor_registration,
#     get_sensor_metadata,
# )

# from aredis_om import (
#     EmbeddedJsonModel,
#     JsonModel,
#     Field,
#     Migrator,
#     get_redis_connection
# )

# from typing import Union

from pydantic import BaseModel

task_list = []

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


# class envdsRegistrar(envdsBase):
#     """docstring for envdsRegistrar."""

#     SENSOR_DEFINITION_REGISTRY = "sensor-definition"
#     SENSOR_REGISTRY = "sensor"
#     INTERFACE_REGISTRY = "interface"
#     SERVICE_REGISTRY = "service"

#     def __init__(self, config=None, **kwargs):
#         super(envdsRegistrar, self).__init__(config, **kwargs)

#         self.update_id("app_uid", "envds-registrar")
#         self.status.set_id_AppID(self.id)

#         self.base_path = "/data"
#         # self.logger = logging.getLogger(self.__class__.__name__)

#         self.file_map = dict()
#         """
#         self.registry = {
#             "services": dict(),
#             "sensors": {
#                 "definitions": {
#                     "make": {
#                         "model": {
#                             "version": "1.0", 
#                             "checksum": "abc", 
#                             "creation_date": "date", 
#                             "metadata": dict()
#                             }
#                     }
#                 },
#                 "instances": dict(),
#             },
#             "interfaces": dict(),
#         }
#         """
#         self.registry = {
#             "services": dict(),
#             "sensors": dict(),
#             # {
#             #     "definitions": dict(),
#             #     "instances": dict(),
#             # },
#             "interfaces": dict(),
#         }

#         # this regsistry will persist on disk
#         self.sensor_definition_registry = {"sensors": dict()}
#         self.run_task_list.append(self.registry_monitor())

#     def configure(self):
#         super(envdsRegistrar, self).configure()

#         # self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/update")
#         # self.router.register_route(key=bet.data_update(), route=self.handle_data)

#     def run_setup(self):
#         super().run_setup()

#         self.logger = logging.getLogger(self.build_app_uid())
#         self.update_id("app_uid", self.build_app_uid())

#         asyncio.create_task(init_db_models())
#         self.load_sensor_definitions()

#     def build_app_uid(self):
#         parts = [
#             "envds-registrar",
#             self.id.app_env_id,
#         ]
#         return (envdsRegistrar.ID_DELIM).join(parts)

#     async def handle_status(self, message: Message):
#         await super().handle_status(message)

#         if message.data["type"] == det.status_update():
#             self.logger.debug("handle_status", extra={"data": message.data})

#     def load_sensor_definitions(self):

#         fname = os.path.join(self.base_path, "envds-registry-sensor-definitions.json")
#         try:
#             with open(fname, "r") as f:
#                 self.sensor_definition_registry = json.load(f)
#         except (FileNotFoundError, json.JSONDecodeError):
#             return

#         try:
#             for make, data1 in self.sensor_definition_registry.items():
#                 for model, data2 in data1.items():
#                     for version, data3 in data2.items():
#                         register_sensor_type(
#                             make=make,
#                             model=model,
#                             version=version,
#                             creation_date=data3["creation_date"],
#                             metadata=data3["metadata"],
#                         )
#         except KeyError:
#             pass

#     def save_sensor_definitions(self):

#         fname = os.path.join(self.base_path, "envds-registry-sensor-definitions.json")
#         with open(fname, "w") as f:
#             json.dump(self.sensor_definition_registry, f)

#     async def handle_data(self, message: Message):
#         # print(f"handle_data: {message.data}")
#         # self.logger.debug("handle_data", extra={"data": message.data})
#         if message.data["type"] == det.data_update():
#             self.logger.debug(
#                 "handle_data",
#                 extra={
#                     "type": det.data_update(),
#                     "data": message.data,
#                     "source_path": message.source_path,
#                 },
#             )

#             src = message.data["source"]
#             # if src not in self.file_map:
#             #     parts = src.split(".")
#             #     sensor_name = parts[-1].split(Sensor.ID_DELIM)
#             #     file_path = os.path.join("/data", "sensor", *sensor_name)

#             #     self.file_map[src] = DataFile(base_path=file_path)
#             #     # await asyncio.sleep(1)
#             #     # if self.file_map[src]:
#             #     #     self.file_map[src].open()
#             #     # await asyncio.sleep(1)
#             # # print(self.file_map[src].base_path)
#             # await self.file_map[src].write_message(message)

#     async def handle_registry(self, message: Message):

#         if message.data["type"] == det.sensor_registry_update():
#             self.logger.debug(
#                 "handle_sensor_registry",
#                 extra={
#                     "type": det.sensor_registry_update(),
#                     "data": message.data,
#                     "source_path": message.source_path,
#                 },
#             )

#             await register_sensor(
#                 make=message.data.data["make"],
#                 model=message.data.data["model"],
#                 serial_number=message.data.data["serial_number"],
#                 source_id=message.data["source"],
#             )

#             # registry update will be for instance
#             #   use instance meta to verify definition is up to date
#             #   check the instance data is up to date

#             # check redis for reg info
#             #   if checksum is same as in self.registry, done
#             #   if checksum is different or not in self.registry, update self.registry
#             #       also, broadcast change in registry to remote systems?

#             src = message.data["source"]
#             # if src not in self.file_map:
#             #     parts = src.split(".")
#             #     sensor_name = parts[-1].split(Sensor.ID_DELIM)
#             #     file_path = os.path.join("/data", "sensor", *sensor_name)

#             #     self.file_map[src] = DataFile(base_path=file_path)
#             #     # await asyncio.sleep(1)
#             #     # if self.file_map[src]:
#             #     #     self.file_map[src].open()
#             #     # await asyncio.sleep(1)
#             # # print(self.file_map[src].base_path)
#             # await self.file_map[src].write_message(message)

#         elif message.data["type"] == det.registry_bcast():
#             if message.data["source"] != self.get_id_as_source():

#                 self.logger.debug(
#                     "handle_registry",
#                     extra={
#                         "type": det.registry_bcast(),
#                         "data": message.data,
#                         "source_path": message.source_path,
#                         "source": message.data["source"],
#                     },
#                 )

#                 try:
#                     if message.data.data["registry"] == self.SENSOR_DEFINITION_REGISTRY:
#                         pass
#                         registries = message.data.data["data"]
#                         for registry in registries:
#                             pass
#                             reg = await get_sensor_type_registration(
#                                 make=registry["make"],
#                                 model=registry["model"],
#                                 version=registry["version"],
#                             )
#                             if reg and registry["checksum"] == reg.checksum:
#                                 continue

#                             req_data = {
#                                 "make": registry["make"],
#                                 "model": registry["model"],
#                                 "version": registry["version"],
#                             }
#                             print(f"req_data: {req_data}")
#                             # request sensor definition
#                             event = DAQEvent.create_registry_request(
#                                 # source="sensor.mockco-mock1-1234", data=record
#                                 source=self.get_id_as_source(),
#                                 data={
#                                     "registry": self.SENSOR_DEFINITION_REGISTRY,
#                                     "data": req_data,
#                                 },
#                             )
#                             # dest_path = f"/{self.get_id_as_topic()}/registry/update"
#                             dest_path = f"/{self.get_id_as_topic()}/registry/request"
#                             self.logger.debug(
#                                 "sensor_definition_monitor",
#                                 extra={"data": event, "dest_path": dest_path},
#                             )
#                             message = Message(data=event, dest_path=dest_path)
#                             # self.logger.debug("default_data_loop", extra={"m": message})
#                             await self.send_message(message)

#                 except KeyError:
#                     pass
#                     # check if sensor definition exists:
#                     #   verify checksum:
#                     #       if not, request metadata

#                 # await register_sensor(
#                 #     make=message.data.data["make"],
#                 #     model=message.data.data["model"],
#                 #     serial_number=message.data.data["serial_number"],
#                 #     source_id=message.data["source"],
#                 # )

#         elif message.data["type"] == det.registry_update():
#             if message.data["source"] != self.get_id_as_source():

#                 self.logger.debug(
#                     "handle_registry",
#                     extra={
#                         "type": det.registry_update(),
#                         "data": message.data,
#                         "source_path": message.source_path,
#                         "source": message.data["source"],
#                     },
#                 )

#                 try:
#                     if message.data.data["registry"] == self.SENSOR_DEFINITION_REGISTRY:
#                         pass
#                         reg = await get_sensor_type_registration(
#                             make=message.data.data["data"]["make"],
#                             model=message.data.data["data"]["model"],
#                             version=message.data.data["data"]["version"],
#                         )
#                         if reg is None or message.data.data["data"]["checksum"] != reg.checksum:
#                             await register_sensor_type(
#                                 # **message.data.data["data"]
#                                 make=message.data.data["data"]["make"],
#                                 model=message.data.data["data"]["model"],
#                                 version=message.data.data["data"]["version"],
#                                 creation_date=message.data.data["data"]["creation_date"],
#                                 metadata=message.data.data["data"]["metadata"],
#                             )

#                 except KeyError:
#                     pass
#                     # check if sensor definition exists:
#                     #   verify checksum:
#                     #       if not, request metadata

#         elif message.data["type"] == det.registry_request():
#             if message.data["source"] != self.get_id_as_source():

#                 self.logger.debug(
#                     "handle_registry",
#                     extra={
#                         "type": det.registry_request(),
#                         "data": message.data,
#                         "source_path": message.source_path,
#                         "source": message.data["source"],
#                     },
#                 )

#                 try:
#                     if message.data.data["registry"] == self.SENSOR_DEFINITION_REGISTRY:
#                         pass
#                         reg = await get_sensor_type_registration(
#                             make=message.data.data["data"]["make"],
#                             model=message.data.data["data"]["model"],
#                             version=message.data.data["data"]["version"],
#                         )
#                         if reg:

#                             resp_data = reg.dict()

#                             # request sensor definition
#                             event = DAQEvent.create_registry_update(
#                                 # source="sensor.mockco-mock1-1234", data=record
#                                 source=self.get_id_as_source(),
#                                 data={
#                                     "registry": self.SENSOR_DEFINITION_REGISTRY,
#                                     "data": resp_data,
#                                 },
#                             )
#                             # dest_path = f"/{self.get_id_as_topic()}/registry/update"
#                             dest_path = f"/{self.get_id_as_topic()}/registry/update"
#                             self.logger.debug(
#                                 "sensor_definition_monitor",
#                                 extra={"data": event, "dest_path": dest_path},
#                             )
#                             message = Message(data=event, dest_path=dest_path)
#                             # self.logger.debug("default_data_loop", extra={"m": message})
#                             await self.send_message(message)

#                 except KeyError:
#                     pass

#     def set_routes(self, enable: bool = True):
#         super(envdsRegistrar, self).set_routes(enable)

#         topic_base = self.get_id_as_topic()

#         print(f"set_routes: {enable}")

#         # self.set_route(
#         #     subscription=f"/envds/{self.id.app_env_id}/sensor/+/data/update",
#         #     route_key=bet.data_update(),
#         #     route=self.handle_data,
#         #     enable=enable
#         # )

#         self.set_route(
#             subscription=f"/envds/+/core/+/registry/bcast",
#             route_key=det.registry_bcast(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         self.set_route(
#             subscription=f"/envds/+/core/+/registry/update",
#             route_key=det.registry_update(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         self.set_route(
#             subscription=f"/envds/+/core/+/registry/request",
#             route_key=det.registry_request(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         self.set_route(
#             subscription=f"/envds/+/sensor/registry/update",
#             route_key=det.sensor_registry_update(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         self.set_route(
#             subscription=f"/envds/+/interface/registry/update",
#             route_key=det.interface_registry_update(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         self.set_route(
#             subscription=f"/envds/+/service/registry/update",
#             route_key=det.service_registry_update(),
#             route=self.handle_registry,
#             enable=enable,
#         )

#         # self.set_route(
#         #     subscription=f"/envds/+/registry/update",
#         #     route_key=bet.registry_update(),
#         #     route=self.handle_registry,
#         #     enable=enable,
#         # )

#         # self.set_route(
#         #     subscription=f"/envds/+/status/update",
#         #     route_key=bet.status_update(),
#         #     route=self.handle_status,
#         #     enable=enable,
#         # )

#         # self.set_route(
#         #     subscription=f"/envds/+/registry/request",
#         #     route_key=bet.registry_request(),
#         #     route=self.handle_registry,
#         #     enable=enable,
#         # )

#         # if enable:
#         #     self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
#         #     self.router.register_route(key=bet.data_update(), route=self.handle_data)
#         # else:
#         #     self.message_client.unsubscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
#         #     self.router.deregister_route(key=bet.data_update(), route=self.handle_data)

#         # self.message_client.subscribe(f"{topic_base}/status/request")
#         # self.router.register_route(key=det.status_request(), route=self.handle_status)
#         # # self.router.register_route(key=et.status_update, route=self.handle_status)

#         # self.router.register_route(key=et.control_request(), route=self.handle_control)
#         # # self.router.register_route(key=et.control_update, route=self.handle_control)

#     async def sensor_monitor(self):

#         try:
#             sensors = await get_all_sensor_registration()
#             self.logger.debug("registered sensors", extra={"sensors": sensors})
#             for sensor in sensors:
#                 print(sensor)
#                 try:
#                     reg = self.registry["sensors"][sensor.pk]
#                 except KeyError:
#                     self.registry["sensors"][sensor.pk] = sensor.dict()

#         except NotFoundError as e:
#             pass

#         print(f"registry: {self.registry}")

#         # do reverse check to clean registry
#         clean = []
#         for pk, sensor in self.registry["sensors"].items():
#             reg = await get_sensor_registration_by_pk(pk)
#             if not reg:
#                 clean.append(pk)

#         for pk in clean:
#             self.registry["sensors"].pop(pk)

#     async def sensor_definition_monitor(self):

#         do_save = False
#         reg_data = []
#         try:
#             self.logger.debug("sensor_definition_monitor")
#             sensors = await get_all_sensor_type_registration()
#             self.logger.debug("registered sensor types", extra={"sensors": sensors})
#             for sensor in sensors:
#                 print(sensor)
#                 try:
#                     # check if in local registry
#                     reg = self.sensor_definition_registry["sensors"][sensor.make][
#                         sensor.model
#                     ][sensor.version]

#                     # if checksums don't match, use new version and save to disk
#                     if reg["checksum"] != sensor.checksum:
#                         reg["checksum"] = sensor.checksum
#                         reg["creation_date"] = sensor.creation_date
#                         reg["metadata"] = sensor.metadata
#                         do_save = True

#                     reg_data.append(sensor.dict(exclude={"metadata"}))
#                     self.logger.debug("reg_data", extra={"data": reg_data})
#                 except KeyError:
#                     if sensor.make not in self.sensor_definition_registry["sensors"]:
#                         self.sensor_definition_registry["sensors"][sensor.make] = {
#                             sensor.model: {
#                                 sensor.version: {
#                                     "checksum": sensor.checksum,
#                                     "creation_date": sensor.creation_date,
#                                     "metadata": sensor.metadata,
#                                 }
#                             }
#                         }
#                     elif (
#                         sensor.model
#                         not in self.sensor_definition_registry["sensors"][sensor.make]
#                     ):
#                         self.sensor_definition_registry["sensors"][sensor.make][
#                             sensor.model
#                         ] = {
#                             sensor.version: {
#                                 "checksum": sensor.checksum,
#                                 "creation_date": sensor.creation_date,
#                                 "metadata": sensor.metadata,
#                             }
#                         }
#                     elif (
#                         sensor.version
#                         not in self.sensor_definition_registry["sensors"][sensor.make][
#                             sensor.model
#                         ]
#                     ):
#                         self.sensor_definition_registry["sensors"][sensor.make][
#                             sensor.model
#                         ][sensor.version] = {
#                             "checksum": sensor.checksum,
#                             "creation_date": sensor.creation_date,
#                             "metadata": sensor.metadata,
#                         }
#                     do_save = True

#             if do_save:
#                 self.logger.debug("sensor_definition_monitor - save to disk")
#                 print(f"sensor definitions: {self.sensor_definition_registry}")
#                 self.save_sensor_definitions()

#             # send registry update for defitions
#             if reg_data:
#                 event = DAQEvent.create_registry_bcast(
#                     # source="sensor.mockco-mock1-1234", data=record
#                     source=self.get_id_as_source(),
#                     data={
#                         "registry": self.SENSOR_DEFINITION_REGISTRY,
#                         "data": reg_data,
#                     },
#                 )
#                 # dest_path = f"/{self.get_id_as_topic()}/registry/update"
#                 dest_path = f"/{self.get_id_as_topic()}/registry/bcast"
#                 self.logger.debug(
#                     "sensor_definition_monitor",
#                     extra={"data": event, "dest_path": dest_path},
#                 )
#                 message = Message(data=event, dest_path=dest_path)
#                 # self.logger.debug("default_data_loop", extra={"m": message})
#                 await self.send_message(message)

#         except NotFoundError as e:
#             self.logger.error("sensor_definition_monitor", extra={"error": e})
#             pass

#         print(f"registry: {self.registry}")

#         # do reverse check to clean registry
#         clean = []
#         for pk, sensor in self.registry["sensors"].items():
#             reg = await get_sensor_registration_by_pk(pk)
#             if not reg:
#                 clean.append(pk)

#         for pk in clean:
#             self.registry["sensors"].pop(pk)

#     async def registry_monitor(self):

#         while True:
#             self.logger.debug("run sensor_monitor")
#             await self.sensor_monitor()
#             # await self.interface_monitor()
#             # await self.service_monitor()

#             self.logger.debug("run sensor_definition_monitor")
#             await self.sensor_definition_monitor()

#             await asyncio.sleep(5)

#     def run(self):
#         super(envdsRegistrar, self).run()

#         self.enable()


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "debug"

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

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("envds-daq")

    # registrar = envdsRegistrar()
    # registrar.run()

    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/daq",
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

    # print(LOGGING_CONFIG)

    # handler = logging.StreamHandler(sys.stdout)
    # formatter = Logfmter(
    #     keys=["at", "when", "name"],
    #     mapping={"at": "levelname", "when": "asctime"},
    #     datefmt=get_datetime_format()
    # )

    # # # self.logger = envdsLogger().get_logger(self.__class__.__name__)
    # # handler.setFormatter(formatter)
    # # # logging.basicConfig(handlers=[handler])
    # root_logger = logging.getLogger(__name__)
    # # # root_logger = logging.getLogger(self.__class__.__name__)
    # # # root_logger.addHandler(handler)
    # root_logger.addHandler(handler)
    # root_logger.setLevel(logging.INFO) # this should be settable
    # root_logger.info("in run", extra={"test": "value"})
    # print(root_logger.__dict__)

    # if "--host" in sys.argv:
    #     print(sys.argv.index("--host"))
    #     print(sys)
    asyncio.run(main(config))
