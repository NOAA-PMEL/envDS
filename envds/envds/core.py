import abc
import os
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
from envds.exceptions import envdsRunTransitionException


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
                    "datefmt": get_datetime_format(fraction=False),
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
    app_env_id: str | None = "default"
    app_group: str | None = "core"
    app_ns: str | None = "envds"
    app_uid: str | None = str(ULID())


#   app_extra: dict | None = {}


class envdsStatus:
    """docstring for envdsStatus."""

    # states
    RUNNING = "running"
    ENABLED = "enabled"

    # values
    UNKNOWN = "unknown"
    TRANSITION = "transition"
    TRUE = "true"
    FALSE = "false"

    def __init__(self, status: dict = None):
        super(envdsStatus, self).__init__()
        if status is None:
            self.status = {"id": {}, "state": {}}
            # self.name = ""
            # self.id = ""
            # self.id = envdsAppID().dict()
            self.set_id_AppID(envdsAppID())
            self.set_state_param(
                envdsStatus.RUNNING,
                requested=envdsStatus.FALSE,
                actual=envdsStatus.FALSE,
            )
            self.set_state_param(
                envdsStatus.ENABLED,
                requested=envdsStatus.FALSE,
                actual=envdsStatus.FALSE,
            )
            # self.state = {
            #     envdsStatus.RUNNING: {
            #         "requested": envdsStatus.UNKNOWN,
            #         "actual": envdsStatus.UNKNOWN
            #     },
            #     envdsStatus.ENABLED: {
            #         "requested": envdsStatus.UNKNOWN,
            #         "actual": envdsStatus.UNKNOWN
            #     },
            # }

        else:
            self.status = status

    def set_id(self, id: dict):
        self.status["id"] = id

    def set_id_AppID(self, id: envdsAppID):
        self.set_id(id.dict())

    def get_id(self):
        return self.status["id"]

    def set_state(self, state: dict):
        self.status["state"] = state

    def set_state_param(self, param: str, requested: str, actual: str):
        self.set_requested(param=param, requested=requested)
        self.set_actual(param=param, actual=actual)

    def get_state(self) -> dict:
        return self.status["state"]

    def get_state_param(self, param):
        try:
            return self.get_state()[param]
        except KeyError:
            return None

    def set_requested(self, param: str, requested: str):
        # if param in self.status["state"]:
        #     self.status["state"][param] = request
        # else:
        #     self.status["state"][param] = {
        #         "requested": request,
        #         "actual": envdsStatus.UNKNOWN
        #     }
        if state := self.get_state_param(param):
            state["requested"] = requested
            self.get_state_param(param)["requested"] = requested
        else:
            self.status["state"][param] = {
                "requested": requested,
                "actual": envdsStatus.UNKNOWN,
            }

    def get_requested(self, param):
        if state := self.get_state_param(param):
            return state["requested"]
        else:
            return None

    def set_actual(self, param: str, actual: str):
        # try:
        if state := self.get_state_param(param):
            # self.status["state"][param] = actual
            state["actual"] = actual
        else:
            # except KeyError:
            self.logger.warn(
                "status_update_actual: unkown param", extra={"param": param}
            )
            pass

    def get_actual(self, param):
        if state := self.get_state_param(param):
            return state["actual"]
        else:
            return None

    def get_status(self):
        return self.status

    def get_health(self) -> bool:
        for name, state in self.status["state"].items():
            if not self.get_health_state(name):
                # if state["requested"] != state["actual"]:
                return False

        return True

    def get_health_state(self, state: str) -> bool:

        try:
            return (
                self.status["state"][state]["requested"]
                == self.status["state"][state]["actual"]
            )
        except KeyError:
            return False


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
        # self.instance_config = {"envds_id": "default"}

        # id fields
        self.id = envdsAppID(
            app_group="core",
            # app_ns="envdsBase",
            app_uid=f"envdsBase-{ULID()}",
        )

        if envds_id := os.getenv("ENVDS_ID"):
            self.update_id("app_env_id", envds_id)

        self.status = envdsStatus()

        # self.id = {
        #     "type": "core",
        #     "name": "envdsBase",
        #     "uid": str(uuid.uuid4())
        # }

        # self.name = "core-envdsBase"
        # self.uid = str(uuid.uuid4())
        # self.logger = logging.getLogger(__name__)

        default_log_level = logging.INFO
        if ll := os.getenv("LOG_LEVEL"):
            try:
                log_level = eval(f"logging.{ll.upper()}")
            except AttributeError:
                log_level = default_log_level
        else:
            log_level = default_log_level
        envdsLogger(level=log_level).init_logger()
        self.logger = logging.getLogger(self.__class__.__name__)
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
        # self.loop.create_task(self.heartbeat())
        # self.do_run = True

        self.run_task_list = []
        self.run_tasks = []
        self.run_tasks.append(asyncio.create_task(self.status_monitor()))
        self.run_task_list.append(self.heartbeat())

        self.enable_task_list = []
        self.enable_tasks = []

        self.config = None
        # self.configure()

        # # set required subs and routes
        # self.message_client.subscribe(f"/envds/status/request")
        # self.router.register_route(key=et.status_request(), route=self.handle_status)
        # # self.router.register_route(key=et.status_update, route=self.handle_status)

        # self.router.register_route(key=et.control_request(), route=self.handle_control)
        # # self.router.register_route(key=et.control_update, route=self.handle_control)

        self.keep_running = True
        # self.msg = Message()

    def configure(self):
        pass

    def set_core_routes(self, enable: bool=True):

        topic_base = self.get_id_as_topic()

        self.set_route(
            subscription=f"{topic_base}/status/request",
            route_key=et.status_request(),
            route=self.handle_status,
            enable=enable
        )

        self.set_route(
            subscription=f"{topic_base}/control/request",
            route_key=et.control_request(),
            route=self.handle_control,
            enable=enable
        )


        # if enable:
        #     self.message_client.subscribe(f"{topic_base}/status/request")
        #     self.router.register_route(key=et.status_request(), route=self.handle_status)
        #     # # self.router.register_route(key=et.status_update, route=self.handle_status)

        #     self.message_client.subscribe(f"{topic_base}/control/request")
        #     self.router.register_route(key=et.control_request(), route=self.handle_control)
        # else:
        #     self.message_client.unsubscribe(f"{topic_base}/status/request")
        #     self.router.deregister_route(key=et.status_request(), route=self.handle_status)
        #     # # self.router.register_route(key=et.status_update, route=self.handle_status)

        #     self.message_client.unsubscribe(f"{topic_base}/control/request")
        #     self.router.deregister_route(key=et.control_request(), route=self.handle_control)

    def set_route(self, subscription: str, route_key: str, route, enable: bool=True):
        
        if enable:
            self.message_client.subscribe(subscription)
            self.router.register_route(key=route_key, route=route)
        else:
            self.message_client.unsubscribe(subscription)
            self.router.deregister_route(key=route_key)

    def set_routes(self, enable: bool=True):
        topic_base = self.get_id_as_topic()
        # add/remove extra routes

    # @abs.abstractmethod
    def get_id(self):
        return self.app_id
        # return ".".join([self.name, self.uid])

    def update_id(self, param, value):
        print(f"update_id: {param}, {value}")
        update = self.id.dict()
        print(update)
        if param in update:
            update[param] = value
            print(update)
            # TODO: need exception handling here
            self.id = envdsAppID(**update)
            print(f"update_id: {self.id}")

    def get_id_string(self):
        parts = []
        for k, v in self.id:
            parts.append(v)
        return ".".join(parts)

    def get_id_as_source(self) -> str:
        return f"{self.id.app_env}.{self.id.app_env_id}.{self.id.app_group}.{self.id.app_uid}"

    def get_id_as_topic(self, delim="/") -> str:
        src = self.get_id_as_source()
        return src.replace(".", delim)
        # return f"{self.id.app_env}.{self.id.app_env_id}.{self.id.app_group}.{self.id.app_uid}"

    # @abc.abstractmethod
    # def handle_id(self, id: str):
    #     parts = id.split("

    def start_message_bus(self):

        self.start_message_buffers()
        self.message_client = MessageClientManager.create()

    def start_message_buffers(self):

        self.buffer_tasks.append(self.loop.create_task(self.send_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.rec_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.message_handler()))

    async def handle_message(self, message: Message):
        """
        Fallback/default message handler for when there is no route
        """
        self.logger.debug(
            "handle_message",
            extra={"source_path": message.source_path, "data": message.data},
        )
        pass

    async def status_monitor(self):

        while True:
            try:
                await self.status_check()
            except Exception as e:
                self.logger.debug("status_monitor error", extra={"e": e})
            await asyncio.sleep(1)

    async def status_check(self):
        # while True:
        #     try:
        if not self.status.get_health():  # something has changed
            # self.logger.debug("status_monitor", extra={"health": self.status.get_health()})
            if not self.status.get_health_state(envdsStatus.ENABLED):
                if self.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
                    try:  # exception raised if already enabling
                        await self.do_enable()
                        # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)
                    except envdsRunTransitionException:
                        pass
                else:
                    try:
                        await self.do_disable()
                    except envdsRunTransitionException:
                        pass

            if not self.status.get_health_state(envdsStatus.RUNNING):
                if self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE:
                    # self.do_run = True
                    asyncio.create_task(self.do_run())
                    # self.status.set_actual(envdsStatus.RUNNING, envdsStatus.TRUE)
                else:
                    await self.do_shutdown()
                    # self.status.set_actual(envdsStatus.RUNNING, envdsStatus.FALSE)
        self.logger.debug("monitor", extra={"status": self.status.get_status()})
        # self.do_run = False
        # except Exception as e:
        #     self.logger.debug("monitor exception", extra={"e": e})

        # await asyncio.sleep(1)

    def enable(self):
        self.status.set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)

    async def do_enable(self):

        requested = self.status.get_requested(envdsStatus.ENABLED)
        actual = self.status.get_actual(envdsStatus.ENABLED)

        if requested != envdsStatus.TRUE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if actual != envdsStatus.FALSE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if not (
            self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE
            and self.status.get_health_state(envdsStatus.RUNNING)
        ):
            return
        # if not self.status.get_health_state(envdsStatus.RUNNING):
        #     return

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRANSITION)

        # add routes
        self.set_routes(True)

        for task in self.enable_task_list:
            self.enable_tasks.append(asyncio.create_task(task))

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)

        # while not self.status.get_health_state(envdsStatus.RUNNING):
        #     print("do_enable: 4")
        #     self.logger.debug("waiting for run state to enable")
        #     await asyncio.sleep(1)

        # while not self.status.get_health_state(envdsStatus.RUNNING):
        #     self.logger.debug("waiting for run health")
        #     await asyncio.sleep(1)

    def disable(self):
        self.status.set_requested(envdsStatus.ENABLED, envdsStatus.FALSE)

    async def do_disable(self):

        requested = self.status.get_requested(envdsStatus.ENABLED)
        actual = self.status.get_actual(envdsStatus.ENABLED)

        if requested != envdsStatus.FALSE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if actual != envdsStatus.TRUE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        # if not (
        #     self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE
        #     and self.status.get_health_state(envdsStatus.RUNNING)
        # ):
        #     return
        # if not self.status.get_health_state(envdsStatus.RUNNING):
        #     return

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRANSITION)

        # add routes
        self.set_routes(False)

        for task in self.enable_tasks:
            if task:
                task.cancel()

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.FALSE)

    async def handle_status(self, message: Message):

        if message.data["type"] == et.status_request():
            self.logger.debug("handle_status", extra={"type": et.status_request()})
            # return status request
        pass

    async def handle_control(self, message: Message):
        pass

    # def handle_data(self, message: Message):
    #     pass

    async def send_message(self, message, **extra):
        if message:
            # remove extra layer of "message" in here for now
            # data = {"message": message}
            # for key, val in extra.items():
            #     data[key] = val
            # self.logger.debug(f"send_message: {data}")
            # # self.logger.debug(f"{self.message_client}")

            # # await self.message_client.send(message)
            # await self.send_buffer.put(data)
            await self.send_buffer.put(message)

    async def send_message_loop(self):

        while True:
            # print("send_message_loop")
            data = await self.send_buffer.get()
            while not self.message_client:
                await asyncio.sleep(0.1)
            await self.message_client.send(data)
            await asyncio.sleep(0.01)

    async def rec_message_loop(self):

        while True:
            if self.message_client:
                data = await self.message_client.get()
                await self.rec_buffer.put(data)
            await asyncio.sleep(0.01)

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
                # print(f"message_handler: {msg}")
                # route = self.router.get_event_route(msg.data)
                # print(f"message_handler: {type(msg)}, {msg.data['type']}")
                route = self.router.route_event(msg.data)
                if route:
                    await route(msg)
                else:
                    await self.handle_message(msg)

                # message = data.pop("message")
                # await self.route(message, extra=data)
            except (TypeError, KeyError):
                self.logger.warn(
                    "messages not in standard format, override 'message_handler'"
                )

    async def heartbeat(self):
        print("heartbeat")
        while True:
            event = envdsEvent.create_status_update(
                # source="envds.core", data={"test": "one", "test2": 2}
                source=self.get_id_as_source(),
                data=self.status.get_status(),
            )
            self.logger.debug("heartbeat", extra={"event": event})
            message = Message(data=event, dest_path="/envds/status/update")
            await self.send_message(message)
            # self.logger.debug("heartbeat", extra={"msg": message})
            await asyncio.sleep(5)

    def init_status(self):
        self.status.set_id_AppID(self.id)
        self.logger.debug("init_status", extra={"status": self.status.get_id()})

    def run(self):
        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.TRUE)
        self.logger.debug("run requested", extra={"status": self.status.get_status()})

    async def do_run(self):

        requested = self.status.get_requested(envdsStatus.RUNNING)
        actual = self.status.get_actual(envdsStatus.RUNNING)

        if requested != envdsStatus.TRUE:
            return
            # raise envdsRunTransitionException(envdsStatus.RUNNING)

        if actual != envdsStatus.FALSE:
            return
            # raise envdsRunTransitionException(envdsStatus.RUNNING)

        self.status.set_actual(envdsStatus.RUNNING, envdsStatus.TRANSITION)

        # set status id
        self.init_status()
        # self.status.set_id_AppID(self.id)

        # self.

        # add core routes
        self.set_core_routes(True)

        # start loop to send status as a heartbeat
        # self.loop.create_task(self.heartbeat())

        for task in self.run_task_list:
            self.run_tasks.append(asyncio.create_task(task))
            self.logger.debug("run_task_list", extra={"data": self.run_tasks})

        self.keep_running = True
        self.status.set_actual(envdsStatus.RUNNING, envdsStatus.TRUE)

        while self.keep_running:
            # print(self.do_run)

            await asyncio.sleep(1)

        self.status.set_actual(envdsStatus.RUNNING, envdsStatus.FALSE)

        # cancel tasks

    async def shutdown(self):
        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.FALSE)

        timeout = 0
        while not self.status.get_health() and timeout < 10:
            timeout += 1
            await asyncio.sleep(1)

    async def do_shutdown(self):
        print("shutdown")

        requested = self.status.get_requested(envdsStatus.RUNNING)
        actual = self.status.get_actual(envdsStatus.RUNNING)

        if requested != envdsStatus.FALSE:
            return
            # raise envdsRunTransitionException(envdsStatus.RUNNING)

        if actual != envdsStatus.TRUE:
            return

        self.message_client.request_shutdown()


        for task in self.run_tasks:
            if task:
                task.cancel()

        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.FALSE)
        self.keep_running = False
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
