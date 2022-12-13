import abc
import sys
import uuid
from ulid import ULID
import asyncio
import logging
from logfmter import Logfmter
# from typing import Union
from pydantic import BaseModel
# from pydantic import BaseSettings, Field
import signal
from envds.util.util import get_datetime_format
from envds.message.message import Message
from envds.message.client import MessageClientManager
from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as et

from envds.message.client import MessageClientManager


class envdsLogger(object):
    """docstring for envdsLogger."""

    def __init__(self, level: str = logging.INFO):
        super(envdsLogger, self).__init__()

        self.log_config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "logfmt": {
                    "()": "logfmter.Logfmter",
                    "keys": ["at", "when", "name"],
                    "mapping": {"at": "levelname", "when": "asctime"},
                    "datefmt": get_datetime_format(),
                },
                "access": {
                    "()": "uvicorn.logging.AccessFormatter",
                    "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
                    "use_colors": True,
                },
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "logfmt"},
                "access": {
                    "formatter": "access",
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                },
            },
            "loggers": {
                "": {"handlers": ["console"], "level": level},
                "uvicorn.access": {
                    "handlers": ["access"],
                    "level": level,
                    "propagate": False,
                },
            },
        }

    def init_logger(self):
        logging.config.dictConfig(self.log_config)

# class clusterID(BaseModel):
#     name: str | None = "default"
#     host: str | None = "127.0.0.1"

# def get_id(self):
#     n = self.name.replace("-", "_")
#     h = self.host.replace("-", "_")
#     h = h.replace(".", "-")
#     return f"{n}-{h}"



# examples:
#   envds.<group>.<class>.<datasystem/namespace>.<uid>
#   envds.core.manager.<cluster-id>
#       e.g., cluster-id: cloudy-10-55-169-51
#   envds.daq.sensor.tsi-3010-1234
class envdsAppID(BaseModel):
  app_env: str | None = "envds"
  app_group: str | None = "core"
  app_class: str | None = "default"
  app_uid: str | None = str(ULID())

class envdsStatus():
    """docstring for envdsStatus."""

    ENABLED = "enbabled"
    CONTROL = "control"

    def __init__(self, status: dict = None):
        super(envdsStatus, self).__init__()

        if status is None:
            self.name = ""
            self.id = ""

            self.state = {
                "enabled": {
                    "requested": "",
                    "actual": ""
                },
                "control": {
                    "requested": "",
                    "actual": ""
                },
            }


class envdsBase(abc.ABC):
    # class envdsBase(object):
    """This is a summary

    Args:
        object (envdsBase): This is a descpription
    """

    def __init__(self, config=None, **kwargs):
        """_summary_

        Args:
            test (_type_, optional): _description_. Defaults to None.
        """
        super(envdsBase, self).__init__()

        self.loop = asyncio.get_event_loop()

        # id fields
        self.id = envdsAppID(
            app_group="core",
            app_class="envdsBase",
            app_uid=str(uuid.uuid4())
        )

        # self.id = {
        #     "type": "core",
        #     "name": "envdsBase",
        #     "uid": str(uuid.uuid4())
        # }

        # self.name = "core-envdsBase"
        # self.uid = str(uuid.uuid4())
        self.logger = logging.getLogger(__name__)
        self.logger.info("Starting envds")

        self.config = config
        self.router = EventRouter()
        self.send_buffer = asyncio.Queue()
        self.rec_buffer = asyncio.Queue()
        self.buffer_tasks = []

        self.message_client = None
        self.start_message_bus()
        # self.start_message_buffers()

        # self.base_tasks = []
        self.loop.create_task(self.heartbeat())
        # self.do_run = True

        self.configure()

        self.do_run = True
        # self.msg = Message()

    def configure(self):
        self.router.register_route(key=et.status_request, route=self.handle_status)
        # self.router.register_route(key=et.status_update, route=self.handle_status)

        self.router.register_route(key=et.control_request, route=self.handle_control)
        # self.router.register_route(key=et.control_update, route=self.handle_control)

        pass

    # @abs.abstractmethod
    def get_id(self):
        return self.app_id
        # return ".".join([self.name, self.uid])
        
    # @abc.abstractmethod
    # def handle_id(self, id: str):
    #     parts = id.split(".")

    def start_message_bus(self):

        self.start_message_buffers()
        self.message_client = MessageClientManager.create()

    def start_message_buffers(self):

        self.buffer_tasks.append(self.loop.create_task(self.send_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.rec_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.message_handler()))

    def handle_message(self, message: Message):
        '''
        Fallback/default message handler for when there is no route
        '''
        self.logger.debug(
            "handle_message",
            extra={"source_path": message.source_path, "data": message.data},
        )
        pass

    def handle_status(self, message: Message):

        if message.data["type"] == et.status_request():
            self.logger.debug("handle_status", extra={"type": et.status_request()})
            # return status request
        pass

    def handle_control(self, message: Message):
        pass

    # def handle_data(self, message: Message):
    #     pass

    async def send_message(self, message, **extra):
        if message:
            data = {"message": message}
            for key, val in extra.items():
                data[key] = val
            self.logger.debug(f"send_message: {data}")
            # self.logger.debug(f"{self.message_client}")

            # await self.message_client.send(message)
            await self.send_buffer.put(data)

    async def send_message_loop(self):

        while True:
            print("send_message_loop")
            data = await self.send_buffer.get()
            while not self.message_client:
                await asyncio.sleep(0.1)
            await self.message_client.send(data)
            await asyncio.sleep(1)

    async def rec_message_loop(self):

        while True:
            if self.message_client:
                data = await self.message_client.get()
                await self.rec_buffer.put(data)
            await asyncio.sleep(0.1)

    async def message_handler(self):
        """
        Parse/unbundle data from message bus. This assumes a standard format where 
        data = {"message": message, "key": "value"...}. This function will extract
        the message and send message and extra data to the router.
        """
        while True:
            # data = await self.rec_buffer.get()
            msg = await self.rec_buffer.get()
            try:
                route = self.router.get_event_route(msg.data)
                if route:
                    route(msg)
                else:
                    self.handle_message(msg)

                # message = data.pop("message")
                # await self.route(message, extra=data)
            except (TypeError, KeyError):
                self.logger.warn(
                    "messages not in standard format, override 'message_handler'"
                )

    async def heartbeat(self):
        print("heartbeat")
        while True:
            print("lub-dub")
            self.logger.info("heartbeat", extra={"test": "one", "test2": 2})
            self.logger.info("test")
            # self.msg.test()
            event = envdsEvent.create_status_update(
                source="envds.core", data={"test": "one", "test2": 2}
            )
            Message(data=event, dest_path="/envds/system/heartbeat")
            await asyncio.sleep(5)

    async def run(self):

        while self.do_run:
            print(self.do_run)
            await asyncio.sleep(1)

        # cancel tasks

    async def shutdown(self):
        print("shutdown")

        self.message_client.request_shutdown()

        self.do_run = False
        # for task in self.base_tasks:
        #     task.cancel()


async def run():
    event_loop = asyncio.get_running_loop()

    test = envdsBase()

    def shutdown_handler(*args):
        asyncio.create_task(test.shutdown())

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    await test.run()


# def request_shutdown():
#     envdsBase.do_run = False


# if __name__ == "__main__":
#     # event_loop = asyncio.get_event_loop()
#     # test = envdsBase()
#     # logger = envdsLogger().init_logger()
#     # logger.info("test")

#     handler = logging.StreamHandler(sys.stdout)
#     formatter = Logfmter(
#         keys=["at", "when", "name"],
#         mapping={"at": "levelname", "when": "asctime"},
#         datefmt=get_datetime_format()
#     )

#     # self.logger = envdsLogger().get_logger(self.__class__.__name__)
#     handler.setFormatter(formatter)
#     # logging.basicConfig(handlers=[handler])
#     root_logger = logging.getLogger(__name__)
#     # root_logger = logging.getLogger(self.__class__.__name__)
#     # root_logger.addHandler(handler)
#     root_logger.addHandler(handler)
#     root_logger.setLevel(logging.DEBUG) # this should be settable
#     root_logger.debug("in run", extra={"test": "value"})

#     # for task in asyncio.all_tasks():
#     #     task.cancel()

#     asyncio.run(run())
#     # request_shutdown()
