from abc import abstractmethod, ABC
import uuid
from ulid import ULID
import logging
import asyncio

import httpx
from logfmter.formatter import Logfmter
from pydantic import BaseSettings, Field
# from asyncio_mqtt import Client, MqttError
import redis.asyncio as redis
from redis.commands.json.path import Path
from cloudevents.http import CloudEvent, from_dict, from_json, to_structured
from cloudevents.conversion import to_json #, from_dict, from_json#, to_structured
from cloudevents.exceptions import InvalidStructuredJSON

# from typing import Union
from pydantic import BaseModel

from envds.message.message import Message
from envds.event.event import envdsEvent as et
from envds.util.util import get_datetime, datetime_to_string, time_to_next

class DBClientConfig(BaseModel):
    type: str | None = "redis"
    # config: dict | None = {"hostname": "localhost", "port": 1883}
    config: dict | None = {"hostname": "localhost"}

# class MessageData(BaseModel):
#     payload: CloudEvent
#     path: Union[str, None] = ""
#     extra: Union[dict, None] = None

#     class Config:
#         arbitrary_types_allowed = True


class DBClientManager():
    """DBClientManager.
    
        Factory class to create DBClients
    """

    @staticmethod
    def create(config: DBClientConfig = None):
        if config is None:
            config = DBClientConfig()

        if config.type == "redis":
            # return redis client
            return RedisDBClient(config)
            pass
        else:
            print("unknown dbclient reqest")
            return None


class DBClient(ABC):
    """docstring for MessageClient."""

    def __init__(self, config: DBClientConfig):
        super(DBClient, self).__init__()

        self.logger = logging.getLogger(__name__)
        self.client_id = ULID()
        self.client = None

        self.config = config

        self.queue_size_limit = 100
        self.put_data = asyncio.Queue()
        self.get_data = asyncio.Queue()
        # self.subscriptions = []

        self.run_task_list = []

        self.do_run = False
        # self.run_state = "RUNNING"
        # self.run_task_list.append(asyncio.create_task(self.publisher()))
        self.run_task_list.append(asyncio.create_task(self.run()))




    async def put(self, data: Message):
        await self.put_data.put(data)
        if self.put_data.qsize() > self.queue_size_limit:
            self.logger.warn(
                "pub_data queue count is %s (limit=%s)",
                self.put_data.qsize(),
                self.queue_size_limit,
            )

    # @abstractmethod
    # async def publisher(self):
    #     pass

    async def get(self) -> Message:
        return await self.sub_data.get()

    # async def run(self):
    #     while self.do_run:
    #         asyncio.sleep(1)

    # # def set_do_run(self, value: bool):
    # #     self.do_run = value

    # # def get_do_run(self):
    # #     return self.do_run

    # def _start(self):
    #     self.do_run = True
    #     self.run_task_list.append(asyncio.create_task(self.publisher()))
    #     self.run_task_list.append(asyncio.create_task(self.run()))

    # async def run(self):
    #     while self.do_run:
    #         await asyncio.sleep(1)

    #     while self.run_state!= "SHUTDOWN":
    #         await asyncio.sleep(1)

    def request_shutdown(self):
        # self.do_run = False
        asyncio.create_task(self.shutdown())

class RedisDBClient(DBClient):
    """docstring for RedisDBClient."""

    def __init__(self, config: DBClientConfig):
        super(RedisDBClient, self).__init__(DBClientConfig)
        self.redis_config = config.config
        self.connected = False
        # self.reconnect_interval = 5
        
        # self._start()
        # self.subscribe(f"mqtt/manage/{self.client_id}")

    # def subscribe(self, topic: str):
    #     asyncio.create_task(self._subscribe(topic))

    # async def _subscribe(self, topic: str):
    #     while self.client is None or not self.connected:
    #         await asyncio.sleep(1)  # wait for client to be ready

    #     await self.client.subscribe(topic)

    # def unsubscribe(self, topic: str):
    #     asyncio.create_task(self._unsubscribe(topic))

    # async def _unsubscribe(self, topic: str):

    #     while self.client is None or not self.connected:
    #         await asyncio.sleep(1)  # wait for client to be ready

    #     await self.client.subscribe(topic)

    async def run(self):

        self.client = redis.from_url(f"redis://{self.redis_config['hostname']}")

        while self.do_run:

            dt = get_datetime()
            record = {
                "time": datetime_to_string(dt),
                "time_1s": datetime_to_string(dt, fraction=False)
            }
            index = str(ULID())
            await self.client.json().set(index, Path.root_path(), record)
            await self.client.expire(index, time=60)
            await asyncio.sleep(time_to_next(1/2))
            # try:
            #     async with Client(hostname=self.redis_config["hostname"]) as self.client:

            #         async with self.client.unfiltered_messages() as messages:

            #             self.connected = True
            #             async for message in messages:
            #                 print(f"message({message.topic}")
            #                 if self.do_run:
            #                     # print(f"listen: {self.do_run}, {self.connected}")
            #                     msg  = Message(data=from_json(message.payload), source_path=message.topic)
            #                     self.logger.debug("mqtt receive message:", extra={"message": msg.data})
            #                     await self.sub_data.put(msg)
            #                     print(
            #                         f"message received: {msg.data}"
            #                         # f"topic: {message.topic}, message: {message.payload.decode()}"
            #                     )
            #                 else:
            #                     print("close messages")
            #                     self.connected = False
            #                     await messages.aclose()

            #                 # print(message.payload.decode())
            #                 # test_count += 1
            # except MqttError as error:
            #     self.connected = False
            #     print(
            #         f'Error "{error}". Reconnecting sub in {self.reconnect_interval} seconds.'
            #     )
            #     await asyncio.sleep(self.reconnect_interval)
            # except Exception as e:
            #     print(e)
        print("done with run")
        self.run_state = "SHUTDOWN"

    async def publisher(self):
        reconnect_interval = 5
        while self.do_run:
            # print(f"publish: {self.do_run}, {self.connected}")
            if self.connected:
                msg = await self.pub_data.get()
                await self.client.publish(msg.dest_path, payload=to_json(msg.data))
            else:
                await asyncio.sleep(1)
            # try:
            #     async with Client(self.mqtt_config["hostname"]) as client:
            #         while self.do_run:
            #             msg = await self.pub_data.get()
            #             await client.publish(msg.dest_path, payload=to_json(msg.data))
            #             # await self.client.publish(md.path, payload=to_json(md.payload))
            #             # await client.publish("measurements/instrument/trh/humidity", payload=json.dumps({"data": 45.1, "units": "%"}))
            #             # await client.publish("measurements/instrument/trh/temperature", payload=json.dumps({"data": 25.3, "units": "degC"}))
            #             # await client.publish("measurements/instrument/trh/pressure", payload=json.dumps({"data": 10013, "units": "Pa"}))
            #             # await client.publish("measurements/instruments/all", payload=json.dumps({"request": "status"}))
            #             # await client.publish("measurements/instrumentgroup/trhgroup", payload=json.dumps({"request": "stop"}))
            #             # await asyncio.sleep(1)
            # except MqttError as error:
            #     print(f'Error "{error}". Reconnecting pub in {reconnect_interval} seconds.')
            #     await asyncio.sleep(reconnect_interval)
        print("done with publisher")

    async def shutdown(self):
        self.do_run = False

        # send a message to trigger the shutdown
        event = et.create_ping(source=f"{self.client_id}")
        await self.put(Message(data=event, dest_path=f"mqtt/manage/{self.client_id}"))
        # self.client.disconnect()
        # await self.messages.aclose()
        # self.connected = False
        # self.do_run = False
        # for task in self.run_task_list:
        #     print(task)
        #     task.cancel()
        # self.connected = False
        # self.do_run = False
        # self.run_state = "SHUTDOWN"
