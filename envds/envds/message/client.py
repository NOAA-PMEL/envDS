from abc import abstractmethod, ABC
import uuid
import ulid
import logging
import asyncio

import httpx
from logfmter.formatter import Logfmter
from pydantic import BaseSettings, Field
from asyncio_mqtt import Client, MqttError
from cloudevents.http import CloudEvent, from_dict, from_json, to_structured
from cloudevents.conversion import to_json  # , from_dict, from_json#, to_structured
from cloudevents.exceptions import InvalidStructuredJSON

# from typing import Union
from pydantic import BaseModel

from envds.message.message import Message
from envds.event.event import envdsEvent as et


class MessageClientConfig(BaseModel):
    type: str | None = "mqtt"
    # config: dict | None = {"hostname": "localhost", "port": 1883}
    config: dict | None = {"hostname": "mosquitto.default", "port": 1883}


# class MessageData(BaseModel):
#     payload: CloudEvent
#     path: Union[str, None] = ""
#     extra: Union[dict, None] = None

#     class Config:
#         arbitrary_types_allowed = True


class MessageClientManager:
    """MessageClientManager.

    Factory class to create MessageClients
    """

    @staticmethod
    def create(config: MessageClientConfig = None):
        if config is None:
            config = MessageClientConfig()

        if config.type == "mqtt":
            # return mqtt client
            return MQTTMessageClient(config)
            pass
        elif config.type == "http":
            # return mqtt client
            return None
            pass
        else:
            print("unknown messageclient reqest")
            return None


class MessageClient(ABC):
    """docstring for MessageClient."""

    def __init__(self, config: MessageClientConfig):
        super(MessageClient, self).__init__()

        self.logger = logging.getLogger(__name__)
        # self.client_id = uuid.uuid4()
        self.client_id = str(ulid.ULID())
        self.client = None

        self.config = config

        self.queue_size_limit = 100
        self.pub_data = asyncio.Queue()
        self.sub_data = asyncio.Queue()
        self.subscriptions = []

        self.run_task_list = []

        self.do_run = False
        # self.run_state = "RUNNING"
        # self.run_task_list.append(asyncio.create_task(self.publisher()))
        # self.run_task_list.append(asyncio.create_task(self.run()))

    async def send(self, data: Message):
        await self.pub_data.put(data)
        if self.pub_data.qsize() > self.queue_size_limit:
            self.logger.warn(
                "pub_data queue count is %s (limit=%s)",
                self.pub_data.qsize(),
                self.queue_size_limit,
            )

    @abstractmethod
    async def publisher(self):
        pass

    async def get(self) -> Message:
        return await self.sub_data.get()

    async def run(self):
        while self.do_run:
            asyncio.sleep(1)

    # def set_do_run(self, value: bool):
    #     self.do_run = value

    # def get_do_run(self):
    #     return self.do_run

    def _start(self):
        self.do_run = True
        self.run_task_list.append(asyncio.create_task(self.publisher()))
        self.run_task_list.append(asyncio.create_task(self.run()))

    # async def run(self):
    #     while self.do_run:
    #         await asyncio.sleep(1)

    #     while self.run_state!= "SHUTDOWN":
    #         await asyncio.sleep(1)

    def request_shutdown(self):
        # self.do_run = False
        asyncio.create_task(self.shutdown())


class MQTTMessageClient(MessageClient):
    """docstring for MQTTMessageClient."""

    def __init__(self, config: MessageClientConfig):
        super(MQTTMessageClient, self).__init__(MessageClientConfig)
        self.mqtt_config = config.config
        self.connected = False
        self.reconnect_interval = 5

        self.subscriptions = []

        self._start()
        self.subscribe(f"/mqtt/manage/{self.client_id}")

    async def _subscribe_all(self):
        for sub in self.subscriptions:
            await self._subscribe(sub)

    def subscribe(self, topic: str):
        if topic not in self.subscriptions:
            self.subscriptions.append(topic)
        asyncio.create_task(self._subscribe(topic))

    async def _subscribe(self, topic: str):
        # while self.client is None or not self.connected:
        #     await asyncio.sleep(1)  # wait for client to be ready
        if self.client:
            try:
                await self.client.subscribe(topic)
            except MqttError as error:
                self.logger.warn("MQTT Client _subscribe: {error}")

    async def _unsubscribe_all(self):
        for sub in self.subscriptions:
            await self._unsubscribe(sub)

    def unsubscribe(self, topic: str):
        asyncio.create_task(self._unsubscribe(topic))

    async def _unsubscribe(self, topic: str):

        while self.client is None or not self.connected:
            await asyncio.sleep(1)  # wait for client to be ready
        if self.client:
            try:
                await self.client.unsubscribe(topic)
            except MqttError as error:
                self.logger.warn("MQTT Client _unsubscribe: {error}")

    async def run(self):

        while self.do_run:
            try:
                # async with Client(hostname=self.mqtt_config["hostname"], client_id=self.client_id) as self.client:
                async with Client(hostname=self.mqtt_config["hostname"]) as self.client:

                    await self._subscribe_all()

                    # async with self.client.unfiltered_messages() as messages:
                    async with self.client.messages() as messages:
                        # print(f"messages: {messages}")
                        self.connected = True
                        async for message in messages:
                            # self.logger.debug(
                            #     "MQTT Client - recv message",
                            #     extra={"topic": message.topic},
                            # )
                            if self.do_run:
                                # print(f"listen: {self.do_run}, {self.connected}")
                                msg = Message(
                                    data=from_json(message.payload),
                                    source_path=message.topic,
                                )
                                # self.logger.debug(
                                #     "mqtt receive message:", extra={"data": msg.data}
                                # )
                                await self.sub_data.put(msg)
                                self.logger.debug(
                                    "MQTT Client - recv message",
                                    extra={
                                        "q": self.sub_data.qsize(),
                                        "payload": message.topic,
                                    },
                                )
                                # print(
                                #     f"message received: {msg.data}"
                                #     # f"topic: {message.topic}, message: {message.payload.decode()}"
                                # )
                            else:
                                # print("close messages")
                                self.connected = False
                                await messages.aclose()

                            # print(message.payload.decode())
                            # test_count += 1
            except MqttError as error:
                self.connected = False
                self.logger.error("MQTT Client MqttError", extra={"error": error})
                # print(
                #     f'Error "{error}". Reconnecting sub in {self.reconnect_interval} seconds.'
                # )
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                self.logger.error("MQTT Client - Exception", extra={"error": e})
                # print(e)
        # self.logger.info("MQTT Client - done")
        # print("done with run")
        self.run_state = "SHUTDOWN"

    async def publisher(self):
        reconnect_interval = 5
        while self.do_run:
            print(f"publish: {self.do_run}, {self.connected}")
            if self.connected:
                msg = await self.pub_data.get()
                # print(f"msg = {msg}")
                # print(f"publisher:msg: {msg}")
                print(f"msg: {msg.dest_path}")#, {to_json(msg.data)}")
                # print(f"msg: {msg.dest_path}, {to_json(msg.data)}")
                # print(msg.keys())
                # print(f"msg type: {type(msg.data)}")
                # bpayload = to_json(msg.data)
                # print(f"bpayload = {bpayload}")
                # payload = bpayload.decode()
                # print(f"payload = {payload}")
                try:
                    dest_path = msg.dest_path
                    if dest_path[0] != "/":
                        dest_path = f"/{dest_path}"
                    await self.client.publish(dest_path, payload=to_json(msg.data))
                    self.logger.debug("MQTT.publisher", extra={"dest_path": dest_path, "payload": to_json(msg.data), "client": self.client})
                    # await self.client.publish(msg.dest_path, payload=payload)
                except MqttError as error:
                    self.logger.error("MQTT Client - MQTTError", extra={"error": error})
                
                await asyncio.sleep(.1)

            else:
                self.logger.debug(
                    "MQTT Client",
                    extra={
                        "self.do_run": self.do_run,
                        "self.connected": self.connected,
                    },
                )
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
        await self.send(Message(data=event, dest_path=f"mqtt/manage/{self.client_id}"))
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
