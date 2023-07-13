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
)

# from envds.message.message import Message
from envds.message.message import Message
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured
from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as bet

# from envds.daq.sensor import Sensor

# from typing import Union

from pydantic import BaseModel

task_list = []


class DataFile:
    def __init__(
        self,
        base_path="/data",
        save_interval=60,
        file_interval="day",
        # config=None,
    ):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.base_path = base_path

        # unless specified, flush file every 60 sec
        self.save_interval = save_interval

        # allow for cases where we want hour files
        #   options: 'day', 'hour'
        self.file_interval = file_interval

        # if config:
        #     self.setup(config)

        # if self.base_path[-1] != '/':
        #     self.base_path += '/'

        self.save_now = True
        # if save_interval == 0:
        #     self.save_now = True

        self.current_file_name = ""

        self.data_buffer = asyncio.Queue()

        self.task_list = []
        self.loop = asyncio.get_event_loop()

        self.file = None

        self.open()

    async def write_message(self, message: Message):
        # print(f"write_message: {message}")
        # print(f"write_message: {message.data}")
        # print(f'{msg.to_json()}')
        await self.write(message.data)
        # if 'body' in msg and 'DATA' in msg['body']:
        #     await self.write(msg['body']['DATA'])

    async def write(self, data_event: CloudEvent):
        # add message to queue and return
        # print(f'write: {data}')
        # print(f"write: {data_event}")
        await self.data_buffer.put(data_event.data)
        qsize = self.data_buffer.qsize()
        if qsize > 5:
            self.logger.warn("write buffer filling up", extra={"qsize": qsize})

    async def __write(self):

        while True:

            data = await self.data_buffer.get()
            # print(f'datafile.__write: {data}')

            try:
                dts = data["variables"]["time"]["data"]
                d_and_t = dts.split("T")
                ymd = d_and_t[0]
                hour = d_and_t[1].split(":")[0]
                # print(f"__write: {dts}, {ymd}, {hour}")
                self.__open(ymd, hour=hour)
                if not self.file:
                    return

                json.dump(data, self.file)
                self.file.write("\n")

                if self.save_now:
                    self.file.flush()
                    if self.save_interval > 0:
                        self.save_now = False

            except KeyError:
                pass

            # if data and ('DATA' in data):
            #     d_and_t = data['DATA']['DATETIME'].split('T')
            #     ymd = d_and_t[0]
            #     hour = d_and_t[1].split(':')[0]

            #     self.__open(ymd, hour=hour)

            #     if not self.file:
            #         return

            #     json.dump(data, self.file)
            #     self.file.write('\n')

            #     if self.save_now:
            #         self.file.flush()
            #         if self.save_interval > 0:
            #             self.save_now = False

    def __open(self, ymd, hour=None):

        fname = ymd
        if self.file_interval == "hour":
            fname += "_" + hour
        fname += ".jsonl"

        # print(f"__open: {self.file}")
        if (
            self.file is not None
            and not self.file.closed
            and os.path.basename(self.file.name) == fname
        ):
            return

        # TODO: change to raise error so __write can catch it
        try:
            # print(f"base_path: {self.base_path}")
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path, exist_ok=True)
        except OSError as e:
            self.logger.error("OSError", extra={"error": e})
            # print(f'OSError: {e}')
            self.file = None
            return
        # print(f"self.file: before")
        self.file = open(
            # self.base_path+fname,
            os.path.join(self.base_path, fname),
            mode="a",
        )
        self.logger.debug(
            "_open",
            extra={"file": self.file, "base_path": self.base_path, "fname": fname},
        )
        # print(f"open: {self.file}, {self.base_path}, {fname}")

    def open(self):
        self.logger.debug("DataFile.open")
        self.task_list.append(asyncio.create_task(self.save_file_loop()))
        self.task_list.append(asyncio.create_task(self.__write()))

    def close(self):

        for t in self.task_list:
            t.cancel()

        if self.file:
            try:
                self.file.flush()
                self.file.close()
                self.file = None
            except ValueError:
                self.logger.info("file already closed")
                # print("file already closed")

    async def save_file_loop(self):

        while True:
            if self.save_interval > 0:
                await asyncio.sleep(time_to_next(self.save_interval))
                self.save_now = True
            else:
                self.save_now = True
                await asyncio.sleep(1)


class envdsFiles(envdsBase):
    """docstring for envdsFiles."""

    def __init__(self, config=None, **kwargs):
        super(envdsFiles, self).__init__(config, **kwargs)

        self.update_id("app_uid", "envds-files")
        self.status.set_id_AppID(self.id)

        # self.logger = logging.getLogger(self.__class__.__name__)

        self.file_map = dict()

        
        # self.run_task_list.append(self._do_run_tasks())

    def configure(self):
        super(envdsFiles, self).configure()

        # self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/update")
        # self.router.register_route(key=bet.data_update(), route=self.handle_data)

    def run_setup(self):
        super().run_setup()

        self.logger = logging.getLogger(self.build_app_uid())
        self.update_id("app_uid", self.build_app_uid())

    def build_app_uid(self):
        parts = [
            "envds-files",
            self.id.app_env_id,
        ]
        return (envdsFiles.ID_DELIM).join(parts)

    async def handle_data(self, message: Message):
        # print(f"handle_data: {message.data}")
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

            src = message.data["source"]
            if src not in self.file_map:
                parts = src.split(".")
                sensor_name = parts[-1].split(self.ID_DELIM)
                file_path = os.path.join("/data", "sensor", *sensor_name)

                self.file_map[src] = DataFile(base_path=file_path)
                # await asyncio.sleep(1)
                # if self.file_map[src]:
                #     self.file_map[src].open()
                # await asyncio.sleep(1)
            # print(self.file_map[src].base_path)
            await self.file_map[src].write_message(message)

    def set_routes(self, enable: bool=True):
        super(envdsFiles, self).set_routes(enable)

        topic_base = self.get_id_as_topic()

        print(f"set_routes: {enable}")

        self.set_route(
            # subscription=f"/envds/{self.id.app_env_id}/sensor/+/data/update",
            subscription=f"/envds/+/sensor/+/data/update",
            route_key=bet.data_update(),
            route=self.handle_data,
            enable=enable,
        )

        # if enable:
        #     self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
        #     self.router.register_route(key=bet.data_update(), route=self.handle_data)
        # else:
        #     self.message_client.unsubscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
        #     self.router.deregister_route(key=bet.data_update(), route=self.handle_data)
       
        # self.message_client.subscribe(f"{topic_base}/status/request")
        # self.router.register_route(key=det.status_request(), route=self.handle_status)
        # # self.router.register_route(key=et.status_update, route=self.handle_status)

        # self.router.register_route(key=et.control_request(), route=self.handle_control)
        # # self.router.register_route(key=et.control_update, route=self.handle_control)

    def run(self):
        print("run:1")
        super(envdsFiles, self).run()
        print("run:2")
        
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
    logger = logging.getLogger("envds-files")

    print("main:1")
    files = envdsFiles()
    print("main:2")
    files.run()
    print("main:3")
    # await asyncio.sleep(2)
    # files.enable()
    # task_list.append(asyncio.create_task(files.run()))
    # await asyncio.sleep(2)

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # # print(LOGGING_CONFIG)
    # dict_config = {
    #     "version": 1,
    #     "disable_existing_loggers": False,
    #     "formatters": {
    #         "logfmt": {
    #             "()": "logfmter.Logfmter",
    #             "keys": ["at", "when", "name"],
    #             "mapping": {"at": "levelname", "when": "asctime"},
    #             "datefmt": get_datetime_format(),
    #         },
    #         "access": {
    #             "()": "uvicorn.logging.AccessFormatter",
    #             "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
    #             "use_colors": True,
    #         },
    #     },
    #     "handlers": {
    #         "console": {"class": "logging.StreamHandler", "formatter": "logfmt"},
    #         "access": {
    #             "formatter": "access",
    #             "class": "logging.StreamHandler",
    #             "stream": "ext://sys.stdout",
    #         },
    #     },
    #     "loggers": {
    #         "": {"handlers": ["console"], "level": "INFO"},
    #         "uvicorn.access": {
    #             "handlers": ["access"],
    #             "level": "INFO",
    #             "propagate": False,
    #         },
    #     },
    # }
    # logging.config.dictConfig(dict_config)

    # envdsLogger().init_logger()
    # logger = logging.getLogger("envds-daq")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))
    # logger.debug("starting envdsFiles")

    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/files",
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
