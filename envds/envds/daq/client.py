import abc
import os
import ulid
import logging
import asyncio

import httpx
from logfmter.formatter import Logfmter
from pydantic import BaseSettings, Field
from asyncio_mqtt import Client, MqttError
from cloudevents.http import CloudEvent, from_dict, from_json, to_structured
from cloudevents.conversion import to_json #, from_dict, from_json#, to_structured
from cloudevents.exceptions import InvalidStructuredJSON

# from typing import Union
from pydantic import BaseModel

from envds.core import envdsAppID, envdsLogger, envdsStatus
from envds.exceptions import envdsRunTransitionException
from envds.message.message import Message
from envds.daq.event import DAQEvent as de
from envds.daq.types import DAQEventType as det

from envds.util.util import (
    # get_datetime_format,
    # time_to_next,
    # get_datetime,
    get_datetime_string,
)

class DAQClientConfig(BaseModel):
    """docstring for ClientConfig."""
    uid: str
    properties: dict | None = {}

    
class DAQClientManager(object):
    """docstring for ClientManager."""
    # def __init__(self):
    #     super(ClientManager, self).__init__()

    @staticmethod
    def create(config: DAQClientConfig, **kwargs):
        pass

class DAQClient(abc.ABC):
    """docstring for Client."""

    # CONNECTED = "connected"

    def __init__(self, config: DAQClientConfig=None, **kwargs):
        super(DAQClient, self).__init__()

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
        self.logger.info("Starting client")

        self.config = config
        if "connect_properties" not in self.config:
            self.config["connect_properties"] = dict()

        self.send_buffer = asyncio.Queue()
        self.recv_buffer = asyncio.Queue()
        # self.buffer_loops = [
        #     asyncio.create_task(self.send_loop()),
        #     asyncio.create_task(self.recv_loop()),
        # ]

        # self.update_id("app_group", "sensor")
        # self.update_id("app_ns", "envds")
        # self.update_id("app_uid", f"make-model-{ULID()}")
        # self.logger.debug("sensor id", extra={"self.id": self.id})

        # self.status.set_id_AppID(self.id)
        # self.status.set_state_param(Sensor.SAMPLING, requested=envdsStatus.FALSE, actual=envdsStatus.FALSE)
        self.run_task_list = []
        self.run_tasks = []
        self.enable_task_list = []
        self.enable_tasks = []

        self.status = envdsStatus()
        # self.status_monitor_task = asyncio.create_task(self.status_monitor())

        self.run_tasks.append(asyncio.create_task(self.status_monitor()))

        self.run_task_list.append(self.recv_loop())
        self.run_task_list.append(self.send_loop())
        self.run_task_list.append(self.client_monitor())


        self.client = None

    async def send(self, data: dict):
        await self.send_buffer.put(data)

    async def recv(self) -> dict:
        data = await self.recv_buffer.get()
        return data

    # async def send_loop(self):
    #     while True:
    #         data = await self.send_buffer.get()
    #         if self.client:
    #             await self.client.send(data)
    #         await asyncio.sleep(.1)

    # async def recv_loop(self):
    #     while True:
    #         if self.client:
    #             data = await self.client.recv()
    #             self.recv_buffer.put(data)
    #         await asyncio.sleep(.1)

    def enable(self) -> None:
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

        if self.client:
            self.client.enable()

        for task in self.enable_task_list:
            self.enable_tasks.append(asyncio.create_task(task))

        # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)

    def disable(self) -> None:
        self.status.set_requested(envdsStatus.ENABLED, envdsStatus.FALSE)

    async def do_disable(self):

        requested = self.status.get_requested(envdsStatus.ENABLED)
        actual = self.status.get_actual(envdsStatus.ENABLED)

        if requested != envdsStatus.FALSE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if actual != envdsStatus.TRUE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if not (
            self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE
            and self.status.get_health_state(envdsStatus.RUNNING)
        ):
            return
        # if not self.status.get_health_state(envdsStatus.RUNNING):
        #     return

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRANSITION)

        if self.client:
            self.client.disable()

        for task in self.enable_task_list:
            if task:
                task.cancel()

        # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)

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

        if self.client:
            if not self.client.status.get_health():
                if self.client.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
                    self.client.enable()
                


        self.logger.debug("monitor", extra={"status": self.status.get_status()})

    def run(self):
        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.TRUE)
        self.logger.debug("run requested", extra={"status": self.status.get_status()})

    # @abc.abstractmethod
    async def open_client(self, config):
        ''' Inherited classes should override this to instatiate the underlying client'''
        return None

    async def close_client(self):
        if self.client:
            self.client.disable()
            self.client = None

    def enabled(self) -> bool:
        if self.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE and self.status.get_health_state(envdsStatus.ENABLED):
            if self.client:
                return self.client.enabled()
        return False

    async def client_monitor(self):

        while True:
            if self.client:
                if not self.client.status.get_health():
                    if self.client.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
                        try:  # exception raised if already enabling
                            await self.client.do_enable()
                            # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)
                        except envdsRunTransitionException:
                            pass
                    else:
                        try:
                            await self.client.do_disable()
                        except envdsRunTransitionException:
                            pass

            await asyncio.sleep(1)

    async def recv_from_client(self):
        return None

    async def recv_loop(self):
        while True:
            msg = await self.recv_from_client()
            if data:
                data = {
                    "timestamp": get_datetime_string(),
                    "data": msg
                }
                self.recv_buffer.put(data)
            await asyncio.sleep(1)

    async def send_to_client(self, data):
        pass

    async def send_loop(self):
        while True:
            data = await self.send_buffer.get()
            await self.send_to_client(data)
            await asyncio.sleep(.1)

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

        # TODO: decide if I need to use AppID in a client
        self.status_set_id(self.config.uid)

        # Instantiate the underlying client
        self.client = await self.open_client(config=self.config)

        # # start data loops
        # asyncio.create_task(self.recv_loop())
        # asyncio.create_task(self.send_loop())

        # # start client status monitor loop
        # asyncio.create_task(self.client_monitor())

        for task in self.run_task_list:
            self.run_tasks.append(asyncio.create_task(task))
        # # set status id
        # self.init_status()
        # # self.status.set_id_AppID(self.id)

        # self.

        # # add core routes
        # self.set_core_routes(True)

        # # start loop to send status as a heartbeat
        # self.loop.create_task(self.heartbeat())

        self.keep_running = True
        self.status.set_actual(envdsStatus.RUNNING, envdsStatus.TRUE)

        while self.keep_running:
            # print(self.do_run)

            await asyncio.sleep(1)

        self.status.set_actual(envdsStatus.RUNNING, envdsStatus.FALSE)

        # cancel tasks

    async def shutdown(self):
        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.FALSE)

        await self.close_client()

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

        # self.message_client.request_shutdown()

        for task in self.run_tasks:
            if task:
                task.cancel()

        self.status.set_requested(envdsStatus.RUNNING, envdsStatus.FALSE)
        self.keep_running = False
        # for task in self.base_tasks:
        #     task.cancel()


class _BaseClient(abc.ABC):
    """docstring for _BaseClient."""
    def __init__(self, config):
        super(_BaseClient, self).__init__()

        self.status = envdsStatus()
        self.status.set_state_param(
            param=envdsStatus.RUNNING,
            requested=envdsStatus.TRUE,
            actual=envdsStatus.TRUE
        )

        self.keep_connected = False

        self.enable_task_list = []
        self.enable_tasks = []
        self.enable_task_list.append(self.do_connect())
    
    def enabled(self) -> bool:
        if self.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
            return self.status.get_health()
        return False
            
    def enable(self):
        self.status.set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)

    def disable(self):
        self.status.set_requested(envdsStatus.ENABLED, envdsStatus.FALSE)

    async def do_enable(self, **kwargs):
        requested = self.status.get_requested(envdsStatus.ENABLED)
        actual = self.status.get_actual(envdsStatus.ENABLED)

        if requested != envdsStatus.TRUE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if actual != envdsStatus.FALSE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRANSITION)

        for task in self.enable_task_list:
            self.enable_tasks.append(asyncio.create_task(task))

        # if not (
        #     self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE
        #     and self.status.get_health_state(envdsStatus.RUNNING)
        # ):
            # return

    async def do_enable(self, **kwargs):
        pass

    async def do_disable(self):
        requested = self.status.get_requested(envdsStatus.ENABLED)
        actual = self.status.get_actual(envdsStatus.ENABLED)

        if requested != envdsStatus.FALSE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        if actual != envdsStatus.TRUE:
            raise envdsRunTransitionException(envdsStatus.ENABLED)

        for task in self.enable_tasks:
            if task:
                task.cancel()
        # if not (
        #     self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE
        #     and self.status.get_health_state(envdsStatus.RUNNING)
        # ):
            # return

class _StreamClient(_BaseClient):
    """docstring for StreamClient."""
    def __init__(self, config):
        super(_BaseClient, self).__init__(config)
        
        self.reader = None
        self.writer = None

    # abc.abstractmethod
    # async def connect(self, **kwargs):
    #     try:
    #         super(_StreamClient, self).connect(**kwargs)
    #     except envdsRunTransitionException:
    #         raise

    async def readline(self, decode_errors="strict"):
        if self.reader:
            msg = await self.reader.readline()
            return msg.decode(errors=decode_errors)

    async def readuntil(
        self,
        terminator='\n',
        decode_errors='strict'
    ):
        if self.reader:
            msg = await self.reader.readuntil(terminator.encode())
            return msg.decode(errors=decode_errors)

    async def read(self, num_bytes=1, decode_errors='strict'):
        if self.reader:
            msg = await self.reader.read(num_bytes)
            return msg.decode(errors=decode_errors)

    async def readbinary(self, num_bytes=1, decode_errors='strict'):
        if self.reader:
            msg = await self.reader.read(num_bytes)
            return msg

    async def write(self, msg):
        if self.writer:
            self.writer.write(msg.encode())
            await self.writer.drain()

    async def writebinary(self, msg):
        if self.writer:
            sent_bytes = self.writer.write(msg)
            await self.writer.drain()

    async def close(self):
        # self.connect_state = ClientConnection.CLOSED
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.status.set_actual(envdsStatus.ENABLED, envdsStatus.FALSE)
