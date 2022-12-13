from abc import abstractmethod
import asyncio
import logging
from cloudevents.http import CloudEvent, event, from_json, to_structured
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields
from gmqtt import Client as MQTTClient
from typing import List

from envds.message.message import Message

class MessageBrokerClientFactory:

    @staticmethod
    def create(config=None, **kwargs):
        logger = logging.getLogger(__class__.__name__)
        if config and "kind" in config and config["kind"] == "envdsBroker":
            try:
                if config["spec"]["type"] == "MQTT":
                    return MQTTBrokerClient(config=config, **kwargs)
            except Exception as e:
                logger.error("Could not create MessageBrokerClient: %s", e)
                return None

class MessageBrokerClient:
    # content_type = "application/json; charset=utf-8"

    def __init__(self, config=None, **kwargs) -> None:
        
        if "event_loop" in kwargs:
            self.loop = kwargs["event_loop"]
        else:
            self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger(self.__class__.__name__)
        
        self.client = None
        self.queue_size_limit = 100

        self.config = None
        self.handle_config(config, **kwargs)
        # self.configure(config, **kwargs)

        self.pub_data = asyncio.Queue()
        self.sub_data = asyncio.Queue()
        self.subscriptions = []

        self.task_list = []

        # TODO: do I need this?
        self.task_list.append(asyncio.get_event_loop().create_task(self.publisher()))
        
        # self.task_list.append(asyncio.get_event_loop().create_task(self.sub_loop()))

        self.task_list.append(asyncio.get_event_loop().create_task(self.connect()))

    @abstractmethod
    def handle_config(self, config=None):
        pass


    @abstractmethod
    def create(self):
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    async def send(self, data):
        await self.pub_data.put(data)
        if self.pub_data.qsize() > self.queue_size_limit:
            self.logger.warn(
                "pub_data queue count is %s (limit=%s)",
                self.pub_data.qsize(),
                self.queue_size_limit,
            )
        # await self.pub_data.set({"channel": channel, "message": message})

    def to_channel(self, source:str, delim=".") -> str:
        '''
        Helper function to convert a source string to a channel string. 
        
        Defaults to MQTT topic format using "/"
        '''
        parts = source.split(delim)
        return "/".join(parts)    

    async def get(self):
        return await self.sub_data.get()

    @abstractmethod
    async def publisher(self):
        pass

    async def subscribe_channel_list(self, channels: List[str]) -> None:
        for channel in channels:
            # if channel not in self.subscriptions:
            #     self.subscriptions.append(channel)
    
            # async allows task to wait until connection is made
            await self.subscribe_channel(channel)

    @abstractmethod
    async def subscribe_channel(self, channel: str):
        pass


class MQTTBrokerClient(MessageBrokerClient):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)
        
        self.create()

    def handle_config(self, config=None, **kwargs):
        super().handle_config(config=config)

        self.config = {
            "client_id": None,
            "host": "localhost",
            "port": 1883,
            "keepalive": 60,
            "clean_session": False,  # need to look at what this means
            "qos_level_pub": 0,
            "qos_level_sub": 0,
            "subscriptions": [],
            "ssl_context": None,
        }
        
        if "client_id" in kwargs:
            self.config["client_id"] = kwargs["client_id"]

        if config and "kind" in config and config["kind"] == "envdsBroker":
            if "host" in config["spec"]:
                self.config["host"] = config["spec"]["host"]
            
            if "port" in config["spec"]:
                self.config["port"] = config["spec"]["port"]

    def create(self):
        super().create()

        if self.config:
            client_config = {
                "client_id": self.config["client_id"],
                "clean_session": self.config["clean_session"],
                # "keepalive": self.config["keepalive"]
            }
            self.client = MQTTClient(**client_config)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_subscribe = self.on_subscribe
            self.client.on_message = self.on_message
            self.logger.debug("client created")

    async def connect(self):

        connect_config = {
            "host": self.config["host"],
            "port": self.config["port"],
            "keepalive": self.config["keepalive"],
        }
        if self.config["ssl_context"]:
            connect_config["ssl"] = self.config["ssl_context"]

        self.logger.debug("connect config: %s", connect_config)
        # await self.client.connect(**connect_config)
        await self.client.connect(connect_config["host"])

    async def disconnect(self):
        for topic in self.subscriptions:
            self.client.unsubscribe(topic)
        await self.client.disconnect()
        self.logger.debug("disconnect")

    async def subscribe_channel(self, channel: str):
        while not self.client.is_connected:
            await asyncio.sleep(1)

        topic = self.to_channel(channel)
        if topic not in self.subscriptions:
            self.subscriptions.append(topic)
        self.client.unsubscribe(topic)
        await asyncio.sleep(.1)
        self.client.subscribe(topic, qos=self.config["qos_level_sub"])
        # return super().subscribe_channel(channel)

    def on_connect(self, client, flags, rc, properties):
        self.logger.debug(
            "%s connected to %s:%s",
            self.config["client_id"],
            self.config["host"],
            self.config["port"],
        )
        self.logger.debug("client connected: client:%s", client)
        self.logger.debug("client connected: flags: %s", flags)
        self.logger.debug("client connected: rc: %s", rc)
        self.logger.debug("client connected: properties: %s", properties)

        self.loop.create_task(self.subscribe_channel_list(self.config["subscriptions"]))

    async def on_message(self, client, topic, payload, qos, properties):
        # print(f"{properties}, {payload}")
        # print(f"{topic}: {payload}")
        # ce = from_json(payload)
        try:
            message = from_json(payload)

            # event = EventData().from_payload(payload)
            data = {"channel": topic, "message": message}
            self.logger.debug("on_message: topic: %s, message: %s", topic, message)
            # qmsg = {"topic": topic, "event": event}
            await self.sub_data.put(data)
            if self.sub_data.qsize() > self.queue_size_limit:
                self.logger.warn(
                    "sub_data queue count is %s (limit=%s)",
                    self.sub_data.qsize(),
                    self.queue_size_limit,
                )
        except InvalidStructuredJSON:
            self.logger.warn("invalid message type %s")

        # await self.from_broker.put(event)
        # self.logger.debug(f'{topic}: {ce["type"]}: {ce["source"]}, {ce.data}')
        # self.logger.debug('%s: %s: %s, {ce.data}', topic, ce["type"], ce["source"])
        return 0

    def on_disconnect(self, client, packet, exc=None):
        self.logger.debug(
            "%s disconnected from %s:%s",
            self.config["client_id"],
            self.config["host"],
            self.config["port"],
        )
        # self.do_run = False

    def on_subscribe(self, client, mid, qos, properties):
        self.logger.debug(
            "%s subscribed to %s",
            self.config["client_id"],
            mid,
            # self.config["client_id"],
            # self.config["host"],
            # self.config["port"],
        )
        # self.logger.info("%s subscribed to %s", self.msg_broker_client_id, mid)

    async def publisher(self):

        wait = True
        while wait:
            if self.client and self.client.is_connected:
                wait = False
            await asyncio.sleep(1)

        # await asyncio.sleep(10)
        while True:
            data = await self.pub_data.get()

            topic = None
            try:
                topic = data["message"]["channel"]
            except KeyError:
                pass
            try:
                topic = data["channel"]
            except KeyError:
                pass
            # if "channel" in data and data["channel"]:
            #     topic = data["channel"]

            if topic:
                header, body = to_structured(data["message"])
                self.client.publish(
                    topic,
                    payload=body,
                    qos=self.config["qos_level_pub"],
                    content_type=Message.content_type,
                )
            else:
                self.logger.warn("attempt to publish to topic=None")
            await asyncio.sleep(0.1)


if __name__ == "__main__":

    broker_config = {
        "apiVersion": "envds/v1", 
        "kind": "envdsBroker", 
        "metadata": {
            "name": "default",
            # "namespace": "envds" # will pick up default
        },
        "spec": {
            "type": "MQTT",
            "host": "localhost",
            "port": 1883,
            "protocol": "TCP"
        }
    }

    client = MessageBrokerClientFactory.create(config=broker_config)
    print(client)

    