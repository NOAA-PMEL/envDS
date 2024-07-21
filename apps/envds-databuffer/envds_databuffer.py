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
    string_to_datetime
)

# import redis.asyncio as redis
# from redis.commands.json.path import Path
from ulid import ULID

# from envds.message.message import Message
from envds.message.message import Message
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured
# from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as bet
from envds.daq.types import DAQEventType as det

from envds.daq.sensor import Sensor
from envds.daq.db import (
    init_db_models,
    SensorDataRecord,
    save_sensor_data,
)

from aredis_om import (
    # EmbeddedJsonModel,
    # JsonModel,
    # Field,
    # Migrator,
    # # get_redis_connection,
    NotFoundError,
)


from pydantic import BaseModel

task_list = []

class envdsDataBuffer(envdsBase):
    """docstring for envdsRegistrar."""

    def __init__(self, config=None, **kwargs):
        super(envdsDataBuffer, self).__init__(config, **kwargs)

        self.update_id("app_uid", "envds-databuffer")
        self.status.set_id_AppID(self.id)

        self.base_path = "/data"
        # self.logger = logging.getLogger(self.__class__.__name__)
     
        self.expire_time = 300
        if "expire" in kwargs:
            self.expire_time = kwargs["expire"]


    def configure(self):
        super(envdsDataBuffer, self).configure()

        # self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/update")
        # self.router.register_route(key=bet.data_update(), route=self.handle_data)

    def run_setup(self):
        super().run_setup()

        self.logger = logging.getLogger(self.build_app_uid())
        self.update_id("app_uid", self.build_app_uid())

        asyncio.create_task(init_db_models())


    def build_app_uid(self):
        parts = [
            "envds-databuffer",
            self.id.app_env_id,
        ]
        return (envdsDataBuffer.ID_DELIM).join(parts)

    # async def handle_status(self, message: Message):
    #     await super().handle_status(message)

    #     if message.data["type"] == bet.status_update():
    #         self.logger.debug("handle_status", extra={"data": message.data})

    # def load_sensor_definitions(self):

    #     fname = os.path.join(self.base_path, "envds-registry-sensor-definitions.json")
    #     try:
    #         with open(fname, "r") as f:
    #             self.sensor_definition_registry = json.load(f)
    #     except (FileNotFoundError,json.JSONDecodeError):
    #         return

    #     for make, data1 in self.sensor_definition_registry.items():
    #         for model, data2 in data1.items():
    #             for version, data3 in data2.items():
    #                 register_sensor_type(
    #                     make=make,
    #                     model=model,
    #                     version=version,
    #                     creation_date=data3["creation_date"],
    #                     metadata=data3["metadata"]
    #                 )

    # def save_sensor_definitions(self):

    #     fname = os.path.join(self.base_path, "envds-registry-sensor-definitions.json")
    #     with open(fname, "w") as f:
    #         json.dump(self.sensor_definition_registry, f)

    async def handle_data(self, message: Message):
        # self.logger.debug("handle_data", extra={"data": message.data})
        if message.data["type"] == bet.data_update():
            self.logger.debug(
                "handle_data",
                extra={
                    "type": bet.data_update(),
                    "data": message.data,
                    "source_path": message.source_path,
                },
            )

            try:
                src = message.data["source"]
                sensor_id = src.split(".")[-1].split("::")
                # record = SensorDataRecord(
                #     make=sensor_id[0],
                #     model=sensor_id[1],
                #     serial_number=sensor_id[2],
                #     timestamp=string_to_datetime(message.data.data["timestamp"]),
                #     source_id=src,
                #     data=message.data.data

                # )
                # print(f"record: {record}")
                # await record.save()
                # await record.expire(self.expire_time)

                await save_sensor_data(
                    make=sensor_id[0],
                    model=sensor_id[1],
                    serial_number=sensor_id[2],
                    timestamp=string_to_datetime(message.data.data["timestamp"]),
                    source_id=src,
                    data=message.data.data,
                    expire=self.expire_time
                )

            except Exception as e:
                self.logger.error("databuffer save error", extra={"error": e})
            # print(f"src: {src}")
            # extract data record and time
            # create SensorDataRecord
            # save to db


            # if src not in self.file_map:
            #     parts = src.split(".")
            #     sensor_name = parts[-1].split(Sensor.ID_DELIM)
            #     file_path = os.path.join("/data", "sensor", *sensor_name)

            #     self.file_map[src] = DataFile(base_path=file_path)
            #     # await asyncio.sleep(1)
            #     # if self.file_map[src]:
            #     #     self.file_map[src].open()
            #     # await asyncio.sleep(1)
            # # print(self.file_map[src].base_path)
            # await self.file_map[src].write_message(message)

    # async def handle_registry(self, message: Message):
    #     if message.data["type"] == det.sensor_registry_update():
    #         self.logger.debug(
    #             "handle_sensor_registry",
    #             extra={
    #                 "type": det.sensor_registry_update(),
    #                 "data": message.data,
    #                 "source_path": message.source_path,
    #             },
    #         )

    #         await register_sensor(
    #             make=message.data.data["make"],
    #             model=message.data.data["model"],
    #             serial_number=message.data.data["serial_number"],
    #             source_id=message.data["source"],
    #         )

    #         # registry update will be for instance
    #         #   use instance meta to verify definition is up to date
    #         #   check the instance data is up to date

    #         # check redis for reg info
    #         #   if checksum is same as in self.registry, done
    #         #   if checksum is different or not in self.registry, update self.registry
    #         #       also, broadcast change in registry to remote systems?

    #         src = message.data["source"]
    #         # if src not in self.file_map:
    #         #     parts = src.split(".")
    #         #     sensor_name = parts[-1].split(Sensor.ID_DELIM)
    #         #     file_path = os.path.join("/data", "sensor", *sensor_name)

    #         #     self.file_map[src] = DataFile(base_path=file_path)
    #         #     # await asyncio.sleep(1)
    #         #     # if self.file_map[src]:
    #         #     #     self.file_map[src].open()
    #         #     # await asyncio.sleep(1)
    #         # # print(self.file_map[src].base_path)
    #         # await self.file_map[src].write_message(message)

    def set_routes(self, enable: bool = True):
        print(f"set_routes: {enable}")
        super(envdsDataBuffer, self).set_routes(enable)

        topic_base = self.get_id_as_topic()

        print(f"set_routes: {enable}")

        self.set_route(
            # subscription=f"/envds/{self.id.app_env_id}/sensor/+/data/update",
            subscription=f"/envds/+/sensor/+/data/update",
            route_key=bet.data_update(),
            route=self.handle_data,
            enable=enable
        )

    def run(self):
        super(envdsDataBuffer, self).run()

        self.enable()



class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("test_task", extra={"test": "daq task"})


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

    print("starting daq test task")

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("envds-databuffer")

    print("main:1")
    buffer = envdsDataBuffer()
    print("main:2")
    buffer.run()
    print("main:3")

    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/databuffer",
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
