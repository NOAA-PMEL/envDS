# import os
# import sys
import asyncio
import logging
import signal
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    time_to_next,
)

from envds.envds.envds import envdsBase, envdsEvent
from envds.message.message import Message
from envds.status.status import Status, StatusEvent


class DAQManager(envdsBase):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)
        pass


class DAQSystem(envdsBase):

    STATUS_STATE_MANAGER = "manager"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.name = "daq-system"
        self.kind = "DAQSystem"
        self.envds_id = ".".join([self.app_sig, "daq", self.namespace, self.name])
        # self.use_namespace = True
        # self.namespace = "default"

        # self.use_namespace = True
        # self.envds_id = ".".join([self.envds_id, "daq"])

        # self.default_subscriptions = []
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_REGISTRY}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_CONTROL}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_DISCOVERY}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_MANAGE}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_STATUS}.request")

        self.manager = None

        self.loop.create_task(self.setup())
        self.do_run = True

        # #TODO: where to add this, wait for self.message_client
        # #      probably in fn to set default subs
        # if config and "part-of" in config:
        #     # part_of = config["part-of"].split(".")
        #     # parent = self.message_client.to_channel(part_of)
        #     # channels = "/".join([parent, "update"])
        #     channel = ".".join([config["part-of"], "+", "update"])
        #     self.default_subscriptions.append(channel)

        # self._daq_map = dict()

        # self.loop.create_task(self.run())

    def handle_config(self, config=None):
        super().handle_config(config=config)

        return

    async def setup(self):
        await super().setup()

        # while not self.status.ready(type=Status.TYPE_CREATE):
        #     self.logger.debug("waiting to create DAQSystem")
        #     await asyncio.sleep(1)
        # await self.create_manager()

        # add subscriptions for requests
        self.apply_subscription(
            ".".join([self.get_id(), "+", "request"])
        )
        # add subscriptions for system/manager
        if self.part_of:
            try:
                self.apply_subscription(
                    ".".join(["envds.system", self.part_of["name"], "+", "update"])
                )
                self.apply_subscription(
                    ".".join(["envds.manager", self.part_of["name"], "+", "update"])
                )
            except KeyError:
                pass

    def set_config(self, config=None):
        # self.use_namespace = True
        return super().set_config(config=config)

    async def create_manager(self, config=None):
        self.logger.debug("creating DataSystemManager client")

        # set status to creating
        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_CREATE,
                state=self.STATUS_STATE_MANAGER,
                status=Status.CREATING,
                ready_status=Status.CREATED,
            )
        )
        self.manager = True
        # self.manager = DAQSystemManager(config=self.config)
        if self.manager:

            # set status to created
            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_CREATE,
                    state=self.STATUS_STATE_MANAGER,
                    status=Status.CREATED,
                )
            )

        # start envdsManager
        # self.manager = DataSystemManager(config=self.config)
        pass

    async def handle_control(self, message, extra=dict()):

        if (action := Message.get_type_action(message)) :

            if action == envdsEvent.TYPE_ACTION_REQUEST:
                data = message.data
                if "run" in data:
                    try:
                        control = data["run"]["type"]
                        value = data["run"]["value"]
                        if control == "shutdown" and value:
                            await self.shutdown()
                    except KeyError:
                        self.logger("invalid run control message")
                        pass

    async def run(self):

        # set status to creating
        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_RUN,
                state=Status.STATE_RUNSTATE,
                status=Status.STARTING,
                ready_status=Status.RUNNING,
            )
        )

        # this part is bootstrapping...need special case for these
        # wait for system to become ready
        # await self.ready_to_run() or something like that
        # if timeout, fail.

        # create DataSystemMananger
        # wait of mananger to become ready
        # manager.ready_to_run
        # if timeout, fail

        while not self.status.ready(type=Status.TYPE_CREATE):
            self.logger.debug("waiting for startup")
            await asyncio.sleep(1)

        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_RUN,
                state=Status.STATE_RUNSTATE,
                status=Status.RUNNING,
            )
        )

        while self.do_run:

            if get_datetime().second % 10 == 0:

                #     # status_event = StatusEvent.create(
                #     #     type=Status.TYPE_RUN,
                #     #     state=Status.STATE_RUNSTATE,
                #     #     status=Status.RUNNING,
                #     # )
                #     # self.status.event(status_event)

                #     status = self.create_status_update(data=self.status.to_dict())
                #     # status = self.create_status_update(
                #     #     {"status": {"time": get_datetime_string(), "value": "OK"}}
                #     # )
                #     await self.send_message(status)
                do_shutdown_req = True
            # self.loop.create_task(self.send_message(status))

            await asyncio.sleep(time_to_next(1))

    async def shutdown(self):

        if (
            self.status.get_current_status(
                type=Status.TYPE_SHUTDOWN, state=Status.STATE_SHUTDOWN
            )
            != Status.SHUTTINGDOWN
        ):

            # set status to creating
            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_SHUTDOWN,
                    state=Status.STATE_SHUTDOWN,
                    status=Status.SHUTTINGDOWN,
                    ready_status=Status.SHUTDOWN,
                )
            )
            # self.status_update_freq = 1

            # simulate waiting for rest of resources to shut down 
            for x in range(0,2):
                self.logger.debug("***simulating DAQSystem shutdown")
                await asyncio.sleep(1)
            
            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_SHUTDOWN,
                    state=Status.STATE_SHUTDOWN,
                    status=Status.SHUTDOWN
                )
            )
            # await asyncio.sleep(2)
            # self.logger.debug("daqsystem: status.ready() = %s", self.status.ready())
            # self.do_run = False
            # timeout = 10
            # sec = 0
            # # allow time for registered services to shutdown and unregister
            # while len(self._daq_map) > 0 and sec <= timeout:
            #     sec += 1
            #     await asyncio.sleep(1)

            # self.logger.info("shutdown")
            # self.run_status = "SHUTDOWN"
            # self.run = False
            # while not self.status.ready():
            #     self.logger.debug("waiting to finish shutdown")
            #     await asyncio.sleep(1)

            while not self.status.ready(type=Status.TYPE_SHUTDOWN):
                self.logger.debug("waiting to finish shutdown")
                await asyncio.sleep(1)

            await super().shutdown()
            self.do_run = False

    # async def run(self):

    #     # apply subscriptions
    #     self.apply_subscriptions(self.default_subscriptions)

    #     self.run_status = "RUNNING"
    #     self.logger.info("daq system %s started", self.namespace)
    #     self.do_run = True
    #     while self.do_run:
    #         if datetime_mod_sec(10) == 0:
    #             # self.logger.debug("%s", sys.path)
    #             status = self.create_status_update({"update": {"value": "OK"}})
    #             await self.send_message(status)

    #         await asyncio.sleep(1)


# from cloudevents.http import event


# class DAQBase(abc.ABC):
#     def __init__(
#         self, daq_id, eventdata_broker=("localhost", 1883), base_file_dir="/tmp/envDS"
#     ) -> None:


# class DAQBase(abc.ABC):
#     def __init__(self) -> None:
#         super().__init__()

#         self.loop = asyncio.get_event_loop()

#         self.logger = logging.getLogger(self.__class__.__name__)
#         self.logger.debug("Starting %s", self.__class__.__name__)

#         self.daq_id = None
#         self.config = None

#         self.eventata_broker = None
#         self.subscriptions = dict()
#         self.event_functions = ["data", "status", "command", "manage", "registry"]
#         self.event_actions = [
#             "update",
#             "request",
#             "enable",
#             "disable",
#             "start",
#             "stop",
#             "shutdown",
#         ]

#         self.send_buffer = asyncio.Queue()
#         self.rec_buffer = asyncio.Queue()

#         self.buffer_tasks = []

#     @abc.abstractmethod
#     def get_id(self):
#         pass

#     @abc.abstractmethod
#     def set_config(self, config=None):
#         pass

#     def start_event_buffers(self):

#         self.buffer_tasks.append(
#             self.loop.create_task(self.send_eventdata_loop())
#         )
#         self.buffer_tasks.append(
#             self.loop.create_task(self.rec_eventdata_loop())
#         )

#     async def send_eventdata_loop(self):
#         pass

#     async def rec_eventdata_loop(self):
#         pass

#     def set_eventdata_broker(self, config=None):
#         if config is None:
#             config = {
#                 "host": "localhost",
#                 "port": 1883,
#                 "keepalive": 60,
#                 "ssl_context": None,
#             }
#         config["client_id"] = self.daq_id
#         self.eventdata_broker = MQTTBroker(
#             config=config
#             # f"DAQManager-{self.namespace}", host=msg_broker[0], port=msg_broker[1]
#         )
#         return self

#     async def route(self, event):
#         # use event["type"] to do initial routing
#         routing_table = {
#             "data": self.handle_data,
#             "status": self.handle_status,
#             "control": self.handle_control,
#             "manage": self.handle_manage,
#             "registry": self.handle_registry,
#         }

#         routed = False
#         for name, fn in routing_table.items():
#             if name in event.get_type().split("."):
#                 await fn(event)
#                 return
#         await self.handle(event)

#     async def handle(self, event):
#         pass

#     async def handle_data(self, event):
#         pass

#     async def handle_status(self, event):
#         pass

#     async def handle_control(self, event):
#         pass

#     async def handle_manage(self, event):
#         pass

#     async def handle_registry(self, event):
#         pass

#         # self.eventdata_broker = eventdata_broker
#         # self.msg_broker_client_id = f"{self.__class__.__name__}_{daq_id}"
#         # # self.msg_broker_client = MQTTClient(self.msg_broker_client_id, clean_session=False)
#         # self.subscribe_list = []

#     # def on_connect(self, client, flags, rc, properties):
#     #     self.logger.info("Connected to %s as %s", self.msg_broker, self.msg_broker_client_id)
#     #     # print('Connected')
#     #     # client.subscribe('envds/instrument/data/#', qos=0)
#     #     # client.subscribe('$SYS/#', qos=0)

#     # async def on_message(self, client, topic, payload, qos, properties):
#     #     # print(f"{properties}, {payload}")
#     #     # print(f"{topic}: {payload}")
#     #     # ce = from_json(payload)
#     #     # self.logger.debug(f'{topic}: {ce["type"]}: {ce["source"]}, {ce.data}')
#     #     # self.logger.debug('%s: %s: %s, {ce.data}', topic, ce["type"], ce["source"])
#     #     return 0

#     # def on_disconnect(self, client, packet, exc=None):
#     #     self.logger.info('%s disconnected from %s',self.msg_broker_client_id, self.msg_broker)

#     # def on_subscribe(self, client, mid, qos, properties):
#     #     self.logger.info("%s subscribed to %s", self.msg_broker_client_id, mid)


# class DAQ(DAQBase):
#     def __init__(
#         self, name="default", msg_broker=("localhost", 1883), base_file_dir="/tmp/envDS"
#     ) -> None:
#         super().__init__(
#             daq_id=name, eventdata_broker=msg_broker, base_file_dir=base_file_dir
#         )


# # class DAQManagerFactory():

# #     _dm_map = dict()
# #     _logger = logging.getLogger("DAQManagerFactory")

# #     async def create(namespace="default", force_replace=False):
# #         if namespace not in DAQManagerFactory()._dm_map:

# #             DAQManagerFactory()._dm_map[namespace] = DAQManager(namespace=namespace)

# #         else:
# #             if force_replace:
# #                 await DAQManagerFactory()._dm_map[namespace].shutdown_all_DAQ()
# #                 DAQManagerFactory()._dm_map[namespace] = DAQManager(namespace=namespace)

# #         return DAQManagerFactory()._dm_map[namespace]


# class DAQManager:

#     _instance = None

#     def __new__(cls):
#         if cls._instance is None:
#             # logger = logging.getLogger(__class__.__name__)
#             # logger.debug("Starting DAQManager: %s", namespace)
#             cls._instance = super(DAQManager, cls).__new__(cls)
#         return cls._instance

#     # def __init__(
#     #     self, namespace="default", msg_broker=("localhost", 1883), base_file_dir="/tmp/envDS"
#     # ) -> None:
#     def __init__(self) -> None:
#         pass
#         # self.stop_event = asyncio.Event()
#         self.loop = asyncio.get_event_loop()

#         self.config = None

#         self.daq_map = dict()
#         self.logger = logging.getLogger(self.__class__.__name__)
#         self.eventdata_broker = None

#         # set defaults
#         self.set_namespace()
#         self.set_eventdata_broker()

#         # self.msg_broker = msg_broker
#         # self.base_file_dir = base_file_dir

#         self.do_run = True
#         asyncio.get_event_loop().add_signal_handler(signal.SIGTERM, self.start_shutdown)
#         # asyncio.get_event_loop().add_signal_handler(signal.SIGIO, self.start_shutdown)

#     def configure(self, config):
#         if self.config and self.config != config:
#             # TODO: need to restart service using new config
#             self.logger.warn("Trying to replace config file!")

#         if "namespace" in config:
#             self.set_namespace(namespace=config["namespace"])

#         if "eventdata_broker" in config:
#             self.set_eventdata_broker(config=config["eventdata_broker"])

#         return self

#     def set_eventdata_broker(self, config=None):
#         if config is None:
#             config = {
#                 "host": "localhost",
#                 "port": 1883,
#                 "keepalive": 60,
#                 "ssl_context": None,
#             }
#         config["client_id"] = f"DAQManager-{self.namespace}"
#         self.eventdata_broker = MQTTBroker(
#             config=config
#             # f"DAQManager-{self.namespace}", host=msg_broker[0], port=msg_broker[1]
#         )
#         return self

#     def set_namespace(self, namespace="default"):
#         self.namespace = namespace
#         self.logger.debug("DAQManager namespace: %s", self.namespace)
#         return self

#     # def start(self):
#     #     asyncio.get_event_loop().create_task(self.run())

#     async def run(self):

#         await self.eventdata_broker.connect()
#         # ping = Message().build_message(source="envds.DAQManager", type="envds.keepalive.PING", data="PING")
#         while self.do_run:
#             self.logger.debug(f"({self.namespace}) keepalive heartbeat")
#             ping = EventData().create(
#                 source="envds.DAQManager",
#                 type="envds.system.manage.PING",
#                 custom={"mqtt_topic": f"DAQManager/{self.namespace}"},
#                 data="PING",
#             )
#             self.logger.debug("event[mqtt_topic] = %s", ping.get_custom("mqtt_topic"))
#             # await self.msg_broker.publish(topic=f"DAQManager/{self.namespace}", message=ping)
#             await self.eventdata_broker.publish(eventdata=ping)
#             await asyncio.sleep(10)

#         # daq = DAQ()

#     async def add_daq(
#         name="default", msg_broker=("localhost", 1883), base_file_dir="/tmp/envDS"
#     ):
#         pass

#     def start_shutdown(self):
#         self.logger.info("Shutdown iniated")
#         # asyncio.create_task(self.shutdown())
#         raise KeyboardInterrupt

#     async def shutdown(self):
#         self.logger.info("Starting shutdown")
#         # print("shutdown:")
#         # for k, controller in controller_map:
#         #     # print(sensor)
#         #     controller.stop()
#         self.do_run = False
#         # if self.server:
#         #     print("server shutdown...")
#         #     await self.server.shutdown()
#         #     print("...done")

#         tasks = asyncio.all_tasks(loop=event_loop)
#         for t in tasks:
#             # print(t)
#             t.cancel()
#         print("Tasks canceled")
#         asyncio.get_event_loop().stop()
#         # await asyncio.sleep(1)


if __name__ == "__main__":
    pass


