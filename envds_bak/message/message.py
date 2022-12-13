from abc import abstractmethod
import asyncio
import sys
from cloudevents.http import CloudEvent, event, from_json, to_structured
from cloudevents.exceptions import InvalidStructuredJSON, MissingRequiredFields
from gmqtt import Client as MQTTClient
from typing import List
import logging


class MessageType:
    APP_PREFIX = "envds"

    TYPE_RUNSTATE = "run-state"
    TYPE_DATA = "data"
    TYPE_STATUS = "status"
    TYPE_CONTROL = "control"
    TYPE_REGISTRY = "registry"
    TYPE_MANAGE = "manage"
    TYPE_DISCOVERY = "discovery"

    TYPE_ACTION_CREATE = "create"
    TYPE_ACTION_UPDATE = "update"
    TYPE_ACTION_DELETE = "delete"
    TYPE_ACTION_REQUEST = "request"
    TYPE_ACTION_RESPONSE = "response"
    TYPE_ACTION_SET = "set"
    TYPE_ACTION_GET = "get"
    TYPE_ACTION_INSERT = "insert"
    TYPE_ACTION_BROADCAST = "broadcast"
    # TYPE_ACTION_ACK = "ack"
    # TYPE_ACTION_NOACK = "noack"

    @staticmethod
    def get_type(type=TYPE_DATA, action=TYPE_ACTION_UPDATE):
        return ".".join([envdsEvent.APP_PREFIX, type, action])


class Message:
    """
    Message Factory helper class to quickly generate messages of common types. All
    methods return a valid CloudEvent or None
    """

    content_type = "application/json; charset=utf-8"
    default_message_types = []
    default_message_type_actions = []

    @staticmethod
    def _create(attributes, data) -> CloudEvent:
        try:
            message = CloudEvent(attributes=attributes, data=data)
        except MissingRequiredFields:
            message = None
        return message

    @staticmethod
    def create(source: str, type: str, data, **kwargs) -> CloudEvent:
        if not source or not type:
            return None

        attributes = {
            "source": source,
            "type": type,
            "datacontenttype" : Message.content_type,
        }
        for key, val in kwargs.items():
            attributes[key] = val
        return Message._create(attributes, data)

    # @staticmethod
    # def create_data(
    #     source: str, service: str, action: str = "update", data=None, **kwargs
    # ) -> CloudEvent:
    #     if not service:
    #         return None
    #     event_type = ".".join(["envds", service, "data", action])
    #     return Message.create(source=source, type=event_type, data=data, **kwargs)
        
    # @staticmethod
    # def create_data_update(source: str, data=None, **kwargs):
    #     return Message.create_data(source=source, action="update", data=data, **kwargs)

    @staticmethod
    def set_default_types(types: List[str]):
        # if Message.default_message_types:
        #     return
        if types:
            for type in types:
                Message.add_default_type(type)
            # Message.default_message_types = types

    @staticmethod
    def add_default_type(type: str) -> None:
        if type and type not in Message.default_message_types:
            Message.default_message_types.append(type)

    @staticmethod
    def set_default_type_actions(actions: List[str]):
        # if Message.default_message_type_actions:
        #     return
        if actions:
            for action in actions:
                Message.add_default_type_action(action)
            # Message.default_message_type_actions = actions

    @staticmethod
    def add_default_type_action(action: str) -> None:
        if action and action not in Message.default_message_type_actions:
            Message.default_message_type_actions.append(action)

    @staticmethod
    def get_type(message, type_list=None):
        if not type_list:
            type_list = Message.default_message_types

        for event_type in type_list:
            if event_type in message["type"].split("."):
                return event_type
        return None

    @staticmethod
    def get_type_action(message, action_list=default_message_type_actions):
        if not action_list:
            action_list = Message.default_message_type_actions

        for action in action_list:
            if action in message["type"].split("."):
                return action
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
        self.configure(config, **kwargs)

        self.pub_data = asyncio.Queue()
        self.sub_data = asyncio.Queue()
        self.subscriptions = []

        self.task_list = []
        self.task_list.append(asyncio.get_event_loop().create_task(self.publisher()))
        # self.task_list.append(asyncio.get_event_loop().create_task(self.sub_loop()))

        self.task_list.append(asyncio.get_event_loop().create_task(self.connect()))

    @abstractmethod
    def configure(self, config, **kwargs):
        pass

    # async def send(self, message, channel=None):
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

    @abstractmethod
    async def publisher(self):
        pass

    async def get(self):
        return await self.sub_data.get()

    @abstractmethod
    async def connect(self):
        pass

    async def close(self):
        # should we flush out the queues first?
        for task in self.task_list:
            task.cancel()

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

        self.create_client()

    def __str__(self) -> str:
        if self.config:
            return (f"{self.__class__.__name__}({self.config['host']}:{self.config['port']})")
        else:
            return (f"{self.__class__.__name__}")

    def configure(self, config, **kwargs):

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
        if config:
            for key, val in config.items():
                self.config[key] = val

        self.logger.debug(f"config: {self.config}")

    def create_client(self):
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
            await self.client.unsubscribe(topic)
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

            # return super().configure(config, **kwargs)

            # # if self.client.is_connected:
            # topic, payload = await self.to_broker.get()
            # self.logger.debug("publish: topic:%s, payload:%s", topic, payload)
            # # self.logger.debug("client: %s", self.client.properties)
            # # if self.client:
            # if topic:
            #     self.client.publish(
            #         topic,
            #         payload=payload,
            #         qos=0,
            #         content_type=MessageBrokerClient.content_type,
            #     )
            # else:
            #     self.logger.warn("attempt to publish to topic=None")
            # await asyncio.sleep(0.1)


async def heartbeat():
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":

    event_loop = asyncio.get_event_loop()
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # , datefmt=isofmt
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    config_sub = {"client_id": "test_sub1", "subscriptions": ["envds/#"]}
    sub_client = MQTTBrokerClient(config=config_sub)
    # sub_client.subscribe_channel("test/test1")

    config_pub = {
        "client_id": "test_pub1",
    }
    pub_client = MQTTBrokerClient(config=config_pub)

    attributes1 = {
        "type": "envds.daq.data.update",
        "source": "/envds/instrument/tsi/3025/2345",
        "datacontenttype": "application/json; charset=utf-8",
        # "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        # "channel": "envds/instrument/tsi/3025/2345",
    }
    attributes2 = {
        "type": "envds.daq.data.update",
        "source": "/envds/instrument/tsi/3025/2345",
        "datacontenttype": "application/json; charset=utf-8",
        # "time": datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        "channel": "envds/instrument/tsi/3025/2345",
    }

    data = {"conc": 1003}
    # event_loop.create_task(
    #     pub_client.send({"channel": 'envds/instrument/tsi/3025/2345', "message": body}
    # )
    data = {"conc": 1003}
    message = CloudEvent(attributes=attributes1, data=data)
    event_loop.create_task(
        pub_client.send(
            {"channel": "envds/instrument/tsi/3025/2345", "message": message}
        )
    )

    data = {"conc": 986}
    message = CloudEvent(attributes=attributes2, data=data)
    event_loop.create_task(pub_client.send({"message": message}))

    # data = {"conc": 1134}
    # message = CloudEvent(attributes=attributes, data=data)
    # event_loop.create_task(pub_client.send({"channel": 'envds/instrument/tsi/3025/2345', "message": message}))
    # data = {"conc": 1094}
    # message = CloudEvent(attributes=attributes, data=data)
    # event_loop.create_task(pub_client.send({"message": message}))

    task_list = asyncio.all_tasks(event_loop)
    # event_loop.run_until_complete(asyncio.wait(task_list))

    event_loop.run_until_complete(heartbeat())
