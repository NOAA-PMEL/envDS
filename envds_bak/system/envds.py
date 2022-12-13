import abc
import sys
import getopt
import argparse
import os
import asyncio
import signal
import logging
import importlib

print(sys.path)
# from envds.registry.registry import envdsRegistry
try:
    from envds.status.status import Status, StatusMonitor, StatusEvent
except ModuleNotFoundError:
    pass

try:
    from envds.message.message import Message
    from envds.message.broker.client import MessageBrokerClientFactory
except ModuleNotFoundError:
    pass

try:
    from envds.util.util import (
        datetime_to_string,
        get_datetime,
        get_datetime_string,
        datetime_mod_sec,
        string_to_datetime,
        time_to_next,
    )
except ModuleNotFoundError:
    pass


class envdsBase(abc.ABC):
    STATUS_STATE_MSGCLIENT = "message-client"

    RUNSTATE_ENABLE = "enable"
    RUNSTATE_DISABLE = "disable"
    RUNSTATE_SHUTDOWN = "shutdown"

    MANAGE_APPLY = "apply"
    MANAGE_DELETE = "delete"

    # STATUS_CREATING = "creating"
    # STATUS_CREATED = "created"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__()

        self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Starting %s", self.__class__.__name__)

        # comment here
        # self.status = StatusMonitor().get_status()
        # self.status_update_freq = 10
        # # self.status_update_freq = 2

        self.app_sig = "envds"
        self.default_namespace = "default"

        # these need to be set by instantiated objects:
        self.kind = None

        self.name = None
        self.envds_id = None

        # self.use_namespace = True  # most things should be namespaced
        self.namespace = None

        # self.part_of = None

        self.config = dict()
        if config:
            # each object should handle their own config.
            #   - broker will be handled by base class
            self.handle_config(config)

        self.message_client = None
        self.subscriptions = dict()

        # # self.logger.debug("path: %s", sys.path)

        self.send_buffer = asyncio.Queue()
        self.rec_buffer = asyncio.Queue()
        self.core_tasks = []

        # self.resource_map = dict()

        # # self.start_message_buffers()

        # # self.config = config

        # # ----

        # # self.use_namespace = True
        # # self.namespace = "default"
        # # self.envds_id = "envds"

        # # self.set_config(config)
        # # # self.config = config
        # # # self.message_broker_config = None

        # # mb_created = False
        # # # self.add_message_broker()
        # # self.loop.create_task(self.add_message_broker())
        # # # if "message_broker" in config:
        # # #     mb_config = config["message_broker"]
        # # #     self.loop.create_task(self.add_message_broker(config=mb_config))
        # # # else:
        # # #     self.logger.error("No message broker configured")
        # # #     self.do_run = False
        # # #     return

        # # self.do_run = True
        # # self.run_status = "STARTING"  # "RUNNING", "SHUTDOWN"

        # # new
        # # start message broker client
        # # pass Namespace to ConfigManager
        # # start ConfigManager (or whatever)
        # # ready to start adding services, etc

    
    # # @abc.abstractmethod
    # # def get_namespace(self):
    # #     pass

    # # @abc.abstractmethod
    # # def get_id(self):
    # #     pass

    def handle_config(self, config=None):

        if config is None:
            return

        # verify config - TODO: check version
        if "kind" in config and "metadata" in config and "spec" in config:
            pass
        else:
            self.logger.error("handle_config: bad config: %s", config)
            self.config = None

        self.config = config

        # common config options

        # broker
        # if config and "kind" in config and config["kind"] == "envdsBroker":
        #     self.config["broker"] = config
        # if "spec" in config and "broker" in config["spec"]:
        #     self.config["broker"] = config["spec"]["broker"]

        # metadata
        try:
            self.kind = config["kind"]
            self.name = config["metadata"]["name"]
        except KeyError:
            pass

        try:
            self.namespace = config["metadata"]["namespace"]
        except KeyError:
            self.namespace = self.default_namespace

        try:
            self.part_of = config["metadata"]["labels"]["part-of"]
        except KeyError:
            pass

    async def setup(self):
        """
        Function to do setup all of the buffers and background processes
        after the configurations are parsed. Needs to be called by child classes. 
        Can be extended by child classes
        """

        # start message buffers
        self.start_message_buffers()

        # start message client
        await self.create_message_client()

        # start status updates
        self.core_tasks.append(self.loop.create_task(self.update_status_loop()))

    # # async def check_for_ready(self):

    # #     while True:
    # #         ready = True
    # #         for condition in self.ready_conditions:
    # #             if not condition.result():
    # #                 self.check_ready_flag = False

    # #         self.check_ready_flag = True
    # #         asyncio.sleep(1)

    # async def check_resources_ready(self, type=Status.TYPE_HEALTH) -> bool:

    #     for ns, ns_map in self.resource_map.items():
    #         for kind, kind_map in ns_map.items():
    #             for name, resource in kind_map.items():
    #                 if resource.status is None or not resource.status.ready(type=type):
    #                     self.logger.debug(
    #                         "%s: status.ready() = %s", name, resource.status.ready()
    #                     )
    #                     return False
    #     return True

    # # def create_message_client(self, config=None):
    # #     self.loop.create_task(self._create_message_client(config=config))
    # # TODO: set status to indicate resource being created
    # async def create_resource(self, config, include_message_broker=True, **kwargs):
    #     if config is None:
    #         return

    #     # verify config
    #     if "kind" in config and "metadata" in config and "spec" in config:
    #         pass
    #     else:
    #         self.logger.error("create_object: bad config: %s", config)

    #     if include_message_broker:
    #         try:
    #             # mb_config = config["message_broker"]
    #             mb_config = config["spec"]["broker"]
    #         except KeyError:
    #             self.logger.info("create_object: adding default broker")
    #             config["spec"]["broker"] = self.config["broker"]

    #     # add 'part-of' if missing

    #     if "labels" not in config["metadata"]:
    #         config["metadata"]["labels"] = dict()
    #     if "part-of" not in config["metadata"]["labels"]:
    #         config["metadata"]["labels"]["part-of"] = {
    #             "kind": self.kind,
    #             "name": self.name,
    #         }

    #     # delete resource if exists - TODO: should call delete_resource
    #     try:
    #         ns = config["metadata"]["namespace"]
    #         kind = config["kind"]
    #         name = config["metadata"]["name"]
    #         resource = self.resource_map[ns][kind][name]
    #         if resource:
    #             await resource.shutdown()
    #         self.resource_map[ns][kind][name] = None
    #     except KeyError:
    #         pass

    #     try:
    #         mod_name = config["spec"]["class"]["module"]
    #         # mod_ = importlib.import_module(config["instance"]["module"])
    #         mod_ = importlib.import_module(mod_name)
    #         class_name = config["spec"]["class"]["class"]
    #         # cls_ = getattr(mod_, config["instance"]["class"])
    #         cls_ = getattr(mod_, class_name)

    #         ns = config["metadata"]["namespace"]
    #         kind = config["kind"]
    #         name = config["metadata"]["name"]
    #         if ns not in self.resource_map:
    #             self.resource_map[ns] = dict()
    #         if kind not in self.resource_map[ns]:
    #             self.resource_map[ns][kind] = dict()
    #         # if config["kind"] not in self.resource_map:
    #         #     self.resource_map[config["kind"]] = dict()
    #         self.resource_map[ns][kind][name] = cls_(config=config, **kwargs)
    #         # self.resource_map[config["kind"]][config["metadata"]["name"]] = cls_(
    #         #     config=config, **kwargs
    #         # )
    #         # resource_id = cls_.get_id()
    #         # prefix = self.message_client.to_channel(cls_.envds_id)
    #         # TODO: check cls_ for what types we should subscribe to. For now, all
    #         # self.apply_subscription(".".join([resource_id, "+", "update"]))
    #         # await asyncio.sleep(2) # wait for resource to be instantiated
    #         id = self.resource_map[ns][kind][name].get_id()
    #         self.apply_subscription(
    #             ".".join([id, "+", "update"])
    #         )

    #     except Exception as e:
    #         self.logger.error(
    #             "%s: could not instantiate service: %s", e, config["name"]
    #         )

    #     return None

    # async def stop_message_client(self):
    #     if self.message_client:
    #         # await self.message_client.stop()
    #         pass

    async def create_message_client(self, config=None):
        self.logger.debug("creating message client")

        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_CREATE,
                state=self.STATUS_STATE_MSGCLIENT,
                status=Status.CREATING,
                ready_status=Status.CREATED,
            )
        )
        # status: message_client.state: creating
        broker_config = None
        if "broker" in self.config:
            broker_config = self.config["broker"]

        try:
            broker_config = self.config["spec"]["broker"]
            type = self.config["spec"]["broker"]["spec"]["type"]
            host = self.config["spec"]["broker"]["spec"]["host"]
            port = self.config["spec"]["broker"]["spec"]["port"]
            self.logger.info(
                "creating %s message broker client for %s:%s ", type, host, port
            )
        except KeyError:
            pass

        # arg will override
        if config and config["kind"] == "envdsBroker":
            try:
                broker_config = config
            except KeyError:
                pass

        self.message_client = None
        if broker_config:
            # broker_config["client_id"] = self.get_id()
            # status: message_client.config = True
            try:
                self.message_client = MessageBrokerClientFactory().create(
                    config=broker_config, client_id=self.get_id()
                )
                self.logger.debug("message_client created")
                self.status.event(
                    StatusEvent.create(
                        type=Status.TYPE_CREATE,
                        state=self.STATUS_STATE_MSGCLIENT,
                        status=Status.CREATED,
                    )
                )

            except Exception as e:
                self.logger.error("could not create message_client: %s", e)
                self.message_client = None
                # throw exception

    def get_id(self):
        # id = self.envds_id
        # if (namespace := self.get_namespace()) :
        #     id = ".".join([id, namespace])
        # return id
        return self.envds_id

    def get_namespace(self):

        if self.use_namespace:
            if not self.namespace:
                return self.default_namespace
            return self.namespace
        return None

    @abc.abstractmethod
    def set_config(self, config=None):
        if config:
            self.config = config

            if self.use_namespace:
                if "namespace" in config:
                    self.namespace = config["namespace"]

            if "message_broker" in config:
                self.message_broker_config = config["message_broker"]

    def start_message_buffers(self):

        self.core_tasks.append(self.loop.create_task(self.send_message_loop()))
        self.core_tasks.append(self.loop.create_task(self.rec_message_loop()))
        self.core_tasks.append(self.loop.create_task(self.message_handler()))

    async def send_message(self, message, **extra):
        if message:
            data = {"message": message}
            for key, val in extra.items():
                data[key] = val
            self.logger.debug("send_message: %s", data)
            # self.logger.debug(f"{self.message_client}")

            # await self.message_client.send(message)
            await self.send_buffer.put(data)

    async def send_message_loop(self):

        while True:
            data = await self.send_buffer.get()
            while not self.message_client:
                await asyncio.sleep(0.1)
            await self.message_client.send(data)
            await asyncio.sleep(0.1)

    async def rec_message_loop(self):

        while True:
            if self.message_client:
                data = await self.message_client.get()
                await self.rec_buffer.put(data)
            await asyncio.sleep(0.1)

    # async def add_message_broker(self, **kwargs):
    #     if not self.config:
    #         self.logger.error("could not instantiate message broker: missing config")
    #         return

    #     try:
    #         self.message_client = kwargs["message_broker_client"]
    #         self.logger.info("message client added: %s", self.message_client)
    #         return
    #     except KeyError:
    #         pass

    #     mb_config = None
    #     if "message_broker" in self.config:
    #         mb_config = self.config["message_broker"]
    #     elif self.message_broker_config:
    #         mb_config = self.message_broker_config

    #     if mb_config:
    #         try:
    #             mod_ = importlib.import_module(
    #                 mb_config["client"]["instance"]["module"]
    #             )
    #             cls_ = getattr(mod_, mb_config["client"]["instance"]["class"])
    #             self.message_client = cls_(config=mb_config, **kwargs)
    #             self.logger.info("message client added: %s", self.message_client)
    #         except Exception as e:
    #             self.logger.error(
    #                 "could not instantiate message broker: %s. config: %s", e, mb_config
    #             )
    #             self.message_client = None

    # def apply_subscriptions(self, subscriptions):
    #     if subscriptions:
    #         self.loop.create_task(
    #             self.message_client.subscribe_channel_list(subscriptions)
    #         )

    # def apply_subscription(self, channel):
    #     if channel:
    #         self.loop.create_task(self.message_client.subscribe_channel(channel))

    # # create message helper functions
    # def create_message(self, type=None, action=None, data=None, target=None, **kwargs):
    #     if not type or not action:
    #         return None

    #     # set default channel using envds_id+action if missing from kwargs
    #     try:
    #         channel = kwargs["channel"]
    #     except KeyError:
    #         if self.message_client:
    #             if target is None:
    #                 target = self.get_id()

    #             kwargs["channel"] = "/".join(
    #                 [self.message_client.to_channel(target), type, action]
    #             )

    #     msg_type = ".".join([envdsEvent.APP_PREFIX, type, action])
    #     return Message.create(source=self.get_id(), type=msg_type, data=data, **kwargs)

    # async def update_status_loop(self):

    #     while not self.status.ready(type=Status.TYPE_CREATE):
    #         self.logger.debug("update_status_loop: waiting for startup")
    #         await asyncio.sleep(1)

    #     while True:
    #         # send status update
    #         data = {
    #             "namespace": self.namespace,
    #             "kind": self.kind,
    #             "name": self.name,
    #             "status": self.status.to_dict()
    #         }
    #         # status = self.create_status_update(data=self.status.to_dict())
    #         status = self.create_status_update(data=data)
    #         await self.send_message(status)

    #         # check registration status, if not registered, do so
    #         await self.update_registration()
    #         # reg_status = self.status.get_current_status(
    #         #         type=Status.TYPE_REGISTRATION, state=Status.STATE_REGISTERED
    #         #     )
    #         # if reg_status not in [Status.REGISTERING, Status.REGISTERED]:
    #         #     self.loop.create_task(self.register())
    #         await asyncio.sleep(self.status_update_freq)

    # def create_status_update(self, data=None, **kwargs):
    #     # self.logger.debug("%s", sys.path)
    #     type = envdsEvent.TYPE_STATUS
    #     action = envdsEvent.TYPE_ACTION_UPDATE
    #     return self.create_message(type=type, action=action, data=data, **kwargs)

    # # def create_data_message(
    # #     self, action=envdsEvent.TYPE_ACTION_UPDATE, data=None, **kwargs
    # # ):
    # #     event_type = ".".join([envdsEvent.TYPE_DATA, action])
    # #     return Message.create(
    # #         source=self.get_id(), type=event_type, data=data, **kwargs
    # #     )

    # async def update_registration(self):

    #     if self.kind == "Registry":
    #         return

    #     reg_status = self.status.get_current_status(
    #         type=Status.TYPE_REGISTRATION, state=Status.STATE_REGISTERED
    #     )
    #     if reg_status != Status.REGISTERED:
    #         if reg_status != Status.REGISTERING:

    #             # subscribe to registry responses
    #             self.apply_subscription(
    #                 ".".join([self.get_id(), envdsEvent.TYPE_REGISTRY, "response"])
    #             )

    #             self.status.event(
    #                 StatusEvent.create(
    #                     type=Status.TYPE_REGISTRATION,
    #                     state=Status.STATE_REGISTERED,
    #                     status=Status.REGISTERING,
    #                     ready_status=Status.REGISTERED,
    #                 )
    #             )

    #         # message = self.create_runstate_request(
    #         #     target=resource.get_id(),
    #         #     data={envdsEvent.TYPE_RUNSTATE: "shutdown"},
    #         # )
    #         # await self.send_message(message)

    #         type = envdsEvent.TYPE_REGISTRY
    #         action = envdsEvent.TYPE_ACTION_REQUEST
    #         data = {envdsEvent.TYPE_REGISTRY: self.config}
    #         message = self.create_registry_request(data=data)
    #         await self.send_message(message)

    #     # check if already in the process of registering
    #     # if reg_status != Status.REGISTERING:

    # async def message_handler(self):
    #     """
    #     Parse/unbundle data from message bus. This assumes a standard format where 
    #     data = {"message": message, "key": "value"...}. This function will extract
    #     the message and send message and extra data to the router.
    #     """
    #     while True:
    #         data = await self.rec_buffer.get()
    #         try:
    #             message = data.pop("message")
    #             await self.route(message, extra=data)
    #         except (TypeError, KeyError):
    #             self.logger.warn(
    #                 "messages not in standard format, override 'message_handler'"
    #             )

    # async def route(self, message, extra=dict()):
    #     # use event["type"] to do initial routing
    #     routing_table = {
    #         envdsEvent.TYPE_DATA: self.handle_data,
    #         envdsEvent.TYPE_STATUS: self.handle_status,
    #         envdsEvent.TYPE_CONTROL: self.handle_control,
    #         envdsEvent.TYPE_MANAGE: self.handle_manage,
    #         envdsEvent.TYPE_REGISTRY: self.handle_registry,
    #         envdsEvent.TYPE_RUNSTATE: self.handle_runstate,
    #     }

    #     # routed = False
    #     self.logger.debug("Message defaults: %s", Message.default_message_types)
    #     try:
    #         fn = routing_table[Message.get_type(message)]
    #         await fn(message, extra=extra)
    #         return
    #     except KeyError:
    #         pass
    #     await self.handle(message, extra=extra)

    #     # for name, fn in routing_table.items():
    #     #     if name in message["type"].split("."):
    #     #         await fn(message, extra=extra)
    #     #         return
    #     # await self.handle(message, extra=extra)

    # async def handle(self, message, extra=dict()):
    #     pass

    # async def handle_data(self, message, extra=dict()):
    #     pass

    # async def handle_status(self, message, extra=dict()):
    #     pass

    # async def handle_control(self, message, extra=dict()):
    #     pass

    # async def handle_manage(self, message, extra=dict()):
    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_REQUEST:
    #             data = message.data
    #             if envdsEvent.TYPE_MANAGE in data:
    #                 if self.MANAGE_APPLY in data[envdsEvent.TYPE_MANAGE]:
    #                     config = data[envdsEvent.TYPE_MANAGE][self.MANAGE_APPLY]
    #                     await self.create_resource(config=config)
    #                     self.logger.debug("apply: create resource")
    #                     # await self.shutdown()
    #                 elif [envdsEvent.TYPE_MANAGE] == self.MANAGE_DELETE:
    #                     self.logger.debug("apply: delete resource")

    # async def handle_registry(self, message, extra=dict()):
    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_RESPONSE:
    #             self.status.event(
    #                 StatusEvent.create(
    #                     type=Status.TYPE_REGISTRATION,
    #                     state=Status.STATE_REGISTERED,
    #                     status=Status.REGISTERED,
    #                 )
    #             )
    #             pass

    # async def handle_runstate(self, message, extra=dict()):

    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_REQUEST:
    #             data = message.data
    #             if envdsEvent.TYPE_RUNSTATE in data:
    #                 if data[envdsEvent.TYPE_RUNSTATE] == self.RUNSTATE_SHUTDOWN:
    #                     await self.shutdown()
    #                 elif data[envdsEvent.TYPE_RUNSTATE] == self.RUNSTATE_DISABLE:
    #                     await self.disable()
    #                 elif data[envdsEvent.TYPE_RUNSTATE] == self.RUNSTATE_ENABLE:
    #                     await self.enable()
    #                 # try:
    #                 #     control = data["run"]["type"]
    #                 #     value = data["run"]["value"]
    #                 #     if control == "shutdown" and value:
    #                 #         await self.shutdown()
    #                 # except KeyError:
    #                 #     self.logger("invalid run control message")
    #                 #     pass

    # def create_runstate_request(self, data=None, target=None, **kwargs):
    #     # self.logger.debug("%s", sys.path)
    #     type = envdsEvent.TYPE_RUNSTATE
    #     action = envdsEvent.TYPE_ACTION_REQUEST
    #     return self.create_message(
    #         type=type, action=action, data=data, target=target, **kwargs
    #     )

    # def create_registry_request(self, data=None, target=None, **kwargs):
    #     # self.logger.debug("%s", sys.path)
    #     if not target:
    #         target = ".".join([self.app_sig, "registry"])
    #     type = envdsEvent.TYPE_REGISTRY
    #     action = envdsEvent.TYPE_ACTION_REQUEST
    #     return self.create_message(
    #         type=type, action=action, data=data, target=target, **kwargs
    #     )

    # async def wait_for_message_client(self) -> bool:
    #     timeout = 10  # seconds
    #     secs = 0
    #     while not self.message_client:
    #         if secs >= timeout:
    #             self.logger.error(
    #                 "PANIC: could not create message client. Check config"
    #             )
    #             return False
    #         secs += 1
    #         await asyncio.sleep(1)
    #     return True

    # async def run(self):

    #     self.run_status = "RUNNING"
    #     while self.do_run:

    #         await asyncio.sleep(1)

    #     self.run_status = "SHUTDOWN"

    # async def shutdown_resources(self):

    #     # send shutdown request to all resources
    #     for ns, ns_map in self.resource_map.items():
    #         for kind, kind_map in ns_map.items():
    #             for name, resource in kind_map.items():
    #                 self.logger.debug(
    #                     "shutdown resource: %s: %s -- %s", kind, name, resource
    #                 )
    #                 self.logger.debug("  resource_id: %s", resource.get_id())

    #                 # send shutdown command to listening services
    #                 message = self.create_runstate_request(
    #                     target=resource.get_id(),
    #                     data={envdsEvent.TYPE_RUNSTATE: "shutdown"},
    #                 )
    #                 await self.send_message(message)

    # async def enable(self):
    #     pass

    # async def disable(self):
    #     pass

    # @abc.abstractmethod
    # async def shutdown(self):
    #     """
    #     Shutdown the base processes. Usually run this at end of derived methods
    #     in child classes
    #     """
    #     self.run_status = "SHUTDOWN"
    #     # while not self.status.ready(type=Status.TYPE_SHUTDOWN):
    #     #     self.logger.debug("waiting to finish shutdown")
    #     #     await asyncio.sleep(1)

    #     if self.message_client:
    #         await self.message_client.disconnect()
    #         self.message_client = None

    #     # shut down message buffers
    #     for task in self.core_tasks:
    #         task.cancel()


# class envdsRegistryLocal(envdsBase):
#     def __init__(self, config=None, **kwargs) -> None:
#         super().__init__(config=config, **kwargs)

#         # self.use_namespace = False
#         self.kind = "Registry"
#         # self.envds_id = ".".join([self.envds_id, "registry"])
#         self.envds_id = ".".join([self.app_sig, "registry"])

#         # self.default_subscriptions = [f"{self.get_id()}/request"]
#         # self.default_subscriptions = []
#         # # self.default_subscriptions.append(f"{self.get_id()}.+.request")
#         # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_REGISTRY}.request")
#         # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_CONTROL}.request")
#         # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_DISCOVERY}.request")
#         # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_MANAGE}.request")
#         # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_STATUS}.request")

#         # #TODO: where to add this, wait for self.message_client
#         # #      probably in fn to set default subs
#         # if config and "part-of" in config:
#         #     # part_of = config["part-of"].split(".")
#         #     # parent = self.message_client.to_channel(part_of)
#         #     # channels = "/".join([parent, "update"])
#         #     channel = ".".join([config["part-of"], "+", "update"])
#         #     self.default_subscriptions.append(channel)

#         self.expired_reg_time = 60
#         self.stale_reg_time = 10
#         self.reg_monitor_time = 2

#         self._registry = dict()
#         self._registry_by_source = dict()

#         # self._registry = {
#         #     "services": None
#         # }

#         # self.logger.info("registry started")
#         # extra = {"channel": "envds/registry/status"}
#         # status = Message.create(
#         #     source=self.envds_id,
#         #     type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
#         #     data={"update": "registry started"},
#         #     **extra,
#         # )
#         # self.loop.create_task(self.send_message(status))
#         # self.loop.create_task(self.run())
#         self.loop.create_task(self.setup())
#         self.do_run = True

#     # async def handle_registry(self, message, extra=dict()):

#     #     if (action := Message.get_type_action(message)) :

#     #         if action == envdsEvent.TYPE_ACTION_REQUEST:
#     #             data = message.data
#     #             if data["request"] == "register":

#     #                 # begin shutting down system
#     #                 # self.logger.info("shutdown requested")
#     #                 # extra = {"channel": "evnds/system/request"}
#     #                 # request = Message.create(
#     #                 #     source=self.envds_id,
#     #                 #     type=envdsEvent.TYPE_ACTION_REQUEST,
#     #                 #     data=data,
#     #                 #     **extra,
#     #                 # )
#     #                 await self.shutdown()

#     def set_config(self, config=None):
#         self.use_namespace = False
#         return super().set_config(config=config)

#     def handle_config(self, config=None):
#         super().handle_config(config=config)

#         return

#     async def setup(self):
#         await super().setup()

#         # while not self.status.ready(type=Status.TYPE_CREATE):
#         #     self.logger.debug("waiting to create DAQSystemManager")
#         #     await asyncio.sleep(1)
#         # await self.create_manager()

#         # add subscriptions for requests
#         self.apply_subscription(".".join([self.get_id(), "+", "request"]))
#         # add subscriptions for system/manager
#         # if self.part_of:
#         #     try:
#         #         self.apply_subscription(
#         #             ".".join(["envds.registry", "request"])
#         #         )
#         #         # self.apply_subscription(
#         #         #     ".".join(["envds.system", self.part_of["name"], "+", "update"])
#         #         # )
#         #         # self.apply_subscription(
#         #         #     ".".join(["envds.manager", self.part_of["name"], "+", "update"])
#         #         # )
#         #     except KeyError:
#         #         pass

#         self.loop.create_task(self.monitor_registry())
#         self.loop.create_task(self.run())

#     async def monitor_registry(self):
#         """
#         Loop to monitor status of registry
#         """
#         while True:
#             for ns, namespace in self._registry.items():
#                 for kname, kind in namespace.items():
#                     for name, reg in kind.items():
#                         # dt = get_datetime()
#                         # lu = reg["last-update"]
#                         # ldt = string_to_datetime(reg["last-update"])
#                         # self.logger.debug("%s", (dt-ldt).seconds)
#                         diff = (
#                             get_datetime() - string_to_datetime(reg["last-update"])
#                         ).seconds
#                         if diff > self.expired_reg_time:
#                             self.logger.debug("%s - %s - %s registration is expired")
#                         elif diff > self.stale_reg_time:
#                             self.logger.debug(
#                                 "%s - %s - %s registration is stale", ns, kname, name
#                             )

#             await asyncio.sleep(self.reg_monitor_time)

#     async def handle_status(self, message, extra=dict()):

#         if (action := Message.get_type_action(message)) :

#             if action == envdsEvent.TYPE_ACTION_UPDATE:
#                 source = message["source"]
#                 self.refresh_registration_by_source(source)

#     async def handle_registry(self, message, extra=dict()):

#         if (action := Message.get_type_action(message)) :

#             if action == envdsEvent.TYPE_ACTION_REQUEST:
#                 source = message["source"]
#                 data = message.data
#                 self.logger.debug("registry request: %s", message)

#                 try:
#                     namespace = data[envdsEvent.TYPE_REGISTRY]["metadata"]["namespace"]
#                     kind = data[envdsEvent.TYPE_REGISTRY]["kind"]
#                     name = data[envdsEvent.TYPE_REGISTRY]["metadata"]["name"]

#                     # create/update _registry
#                     if namespace not in self._registry:
#                         self._registry[namespace] = dict()
#                     if kind not in self._registry[namespace]:
#                         self._registry[namespace][kind] = dict()
#                     self._registry[namespace][kind][name] = {
#                         "source": source,
#                         "created": get_datetime_string(),
#                         "last-update": get_datetime_string(),
#                     }

#                     # create/update _registry_by_source
#                     self._registry_by_source[source] = {
#                         "namespace": namespace,
#                         "kind": kind,
#                         "name": name,
#                     }

#                     data = {envdsEvent.TYPE_REGISTRY: "registered"}
#                     response = self.create_registry_response(target=source, data=data)
#                     await self.send_message(response)

#                     # subscribe to status updates to refresh registry
#                     self.apply_subscription(
#                         ".".join([source, envdsEvent.TYPE_STATUS, "update"])
#                     )

#                 except KeyError:
#                     self.logger.info("could not register %s", source)
#                     return

#                 # if "run" in data:
#                 #     try:
#                 #         control = data["run"]["type"]
#                 #         value = data["run"]["value"]
#                 #         if control == "shutdown" and value:
#                 #             await self.shutdown()
#                 #     except KeyError:
#                 #         self.logger("invalid run control message")
#                 #         pass

#     def refresh_registration_by_source(self, source):
#         if reg := self.get_registration_by_source(source):
#             try:
#                 ns = reg["namespace"]
#                 kind = reg["kind"]
#                 name = reg["name"]
#                 self._registry[ns][kind][name]["last-update"] = get_datetime_string()
#             except KeyError:
#                 pass

#     def update_registration(self, source, namespace, kind, name):

#         if not all([source, namespace, kind, name]):
#             self.logger.debug("can't update registration")
#             return

#         # create/update _registry
#         if namespace not in self._registry:
#             self._registry[namespace] = dict()
#         if kind not in self._registry[namespace]:
#             self._registry[namespace][kind] = dict()
#         self._registry[namespace][kind][name] = {
#             "source": source,
#             "created": get_datetime_string(),
#             "last-update": get_datetime_string(),
#         }

#         # create/update _registry_by_source
#         self._registry_by_source[source] = {
#             "namespace": namespace,
#             "kind": kind,
#             "name": name,
#         }

#     def get_registration_filter(self, namespace=None, kind=None, name=None):
#         # allow user to get a list of registrations based on a filter
#         pass

#     def get_registration(self, namespace, kind, name):
#         if not all([namespace, kind, name]):
#             self.logger.debug("can't get registration")
#             return None

#         try:
#             return self._registry[namespace][kind][name]
#         except KeyError:
#             return None

#     def get_registration_by_source(self, source):
#         if not source:
#             self.logger.debug("can't get registration_by_source")
#             return None

#         try:
#             reg = self._registry_by_source[source]
#             return reg
#             # return self.get_registration(meta["namespace"], meta["kind"], meta["name"])
#         except KeyError:
#             return None

#     def create_registry_response(self, target=None, data=None, **kwargs):
#         if not target:
#             target = ".".join([self.app_sig, "registry"])
#         type = envdsEvent.TYPE_REGISTRY
#         action = envdsEvent.TYPE_ACTION_RESPONSE
#         return self.create_message(
#             type=type, action=action, data=data, target=target, **kwargs
#         )

#     # async def handle_control(self, message, extra=dict()):

#     #     if (action := Message.get_type_action(message)) :

#     #         if action == envdsEvent.TYPE_ACTION_REQUEST:
#     #             data = message.data
#     #             if "run" in data:
#     #                 try:
#     #                     control = data["run"]["type"]
#     #                     value = data["run"]["value"]
#     #                     if control == "shutdown" and value:
#     #                         await self.shutdown()
#     #                 except KeyError:
#     #                     self.logger("invalid run control message")
#     #                     pass

#     async def shutdown(self):
#         timeout = 10
#         sec = 0
#         # allow time for registered services to shutdown and unregister
#         while len(self._registry) > 0 and sec <= timeout:
#             sec += 1
#             await asyncio.sleep(1)

#         self.logger.info("shutdown")
#         self.run_status = "SHUTDOWN"
#         self.run = False
#         return await super().shutdown()

#     async def run(self):

#         # set status to creating
#         self.status.event(
#             StatusEvent.create(
#                 type=Status.TYPE_RUN,
#                 state=Status.STATE_RUNSTATE,
#                 status=Status.STARTING,
#                 ready_status=Status.RUNNING,
#             )
#         )

#         while not self.status.ready(type=Status.TYPE_CREATE):
#             self.logger.debug("waiting for startup")
#             await asyncio.sleep(1)

#         self.status.event(
#             StatusEvent.create(
#                 type=Status.TYPE_RUN,
#                 state=Status.STATE_RUNSTATE,
#                 status=Status.RUNNING,
#             )
#         )

#         # apply subscriptions
#         # self.apply_subscriptions(self.default_subscriptions)

#         # self.run_status = "RUNNING"
#         # self.logger.info("registry started")
#         # self.do_run = True
#         while self.do_run:
#             # if datetime_mod_sec(10) == 0:
#             #     # self.logger.debug("%s", sys.path)
#             #     status = self.create_status_update({"update": {"value": "OK"}})
#             #     await self.send_message(status)

#             #         extra = {"channel": "envds/registry/status"}
#             #         status = Message.create(
#             #             source=self.envds_id,
#             #             type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
#             #             data={"update": "registry started"},
#             #             **extra,
#             #         )
#             #         self.logger.debug(self.message_client)
#             #         await self.send_message(status)
#             #     # self.loop.create_task(self.send_message(status))
#             await asyncio.sleep(1)

#         # return await super().run()

#     async def shutdown(self):

#         if (
#             self.status.get_current_status(
#                 type=Status.TYPE_SHUTDOWN, state=Status.STATE_SHUTDOWN
#             )
#             != Status.SHUTTINGDOWN
#         ):

#             # set status to creating
#             self.status.event(
#                 StatusEvent.create(
#                     type=Status.TYPE_SHUTDOWN,
#                     state=Status.STATE_SHUTDOWN,
#                     status=Status.SHUTTINGDOWN,
#                     ready_status=Status.SHUTDOWN,
#                 )
#             )
#             # self.status_update_freq = 1

#             # simulate waiting for rest of resources to shut down
#             # for x in range(0,2):
#             #     self.logger.debug("***simulating DAQSystem shutdown")
#             #     await asyncio.sleep(1)

#             # give a moment to let message propogate
#             await asyncio.sleep(2)

#             self.status.event(
#                 StatusEvent.create(
#                     type=Status.TYPE_SHUTDOWN,
#                     state=Status.STATE_SHUTDOWN,
#                     status=Status.SHUTDOWN,
#                 )
#             )
#             # await asyncio.sleep(2)
#             # self.logger.debug("daqsystem: status.ready() = %s", self.status.ready())
#             # self.do_run = False
#             # timeout = 10
#             # sec = 0
#             # # allow time for registered services to shutdown and unregister
#             # while len(self._daq_map) > 0 and sec <= timeout:
#             #     sec += 1
#             #     await asyncio.sleep(1)

#             # self.logger.info("shutdown")
#             # self.run_status = "SHUTDOWN"
#             # self.run = False
#             # while not self.status.ready():
#             #     self.logger.debug("waiting to finish shutdown")
#             #     await asyncio.sleep(1)

#             while not self.status.ready(type=Status.TYPE_SHUTDOWN):
#                 self.logger.debug("waiting to finish shutdown")
#                 await asyncio.sleep(1)

#             await super().shutdown()
#             self.do_run = False

    # async def run(self):
    #     self.logger.info("registry started")
    #     extra = {"channel": "envds/registry/status"}
    #     status = Message.create(
    #         source=self.envds_id,
    #         type=Message.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
    #         data={"update": "registry started"},
    #         **extra,
    #     )
    #     self.send_message(status)
    #     return await super().run()


# class DataSystemManager(envdsBase):
#     """
#     Manager class that creates the platform/infrastructure to run the envds services. 
#     """

#     def __init__(self, config=None, **kwargs) -> None:
#         super().__init__(config=config, **kwargs)

#         # # default/base namespace for envds
#         # self.namespace = "envds"
#         # namespace = { # envds namespace
#         #     "apiVersion": "envds/v1",
#         #     "kind": "Namespace",
#         #     "metadata": {
#         #         "name": self.namespace
#         #     }
#         # }
#         # self.add_broker_client()
#         # self.create_config_manager([namespace, self.config])

#         # ----
#         self.use_namespace = False
#         self.kind = "DataSystemManager"
#         self.namespace = "envds"
#         # self.name = "envds-manager"
#         self.envds_id = ".".join([self.app_sig, "manager", self.name])

#         self.loop.create_task(self.setup())
#         self.do_run = True

#         self.service_map = dict()
#         self.system_map = {
#             # <namespace>: <kind>: <name> : {config}
#             # "envds": {  # these really won't be used but it gives the template
#             #     "DAQSystem": {"envds-system": {"config": "here", "status": "here"}},
#             #     "DAQManager": {"envds-manager": {"config": "here"}},
#             # }
#         }

#         self.system_map_by_id = dict()

#     async def apply(self, config=None):
#         if config is None:
#             return

#         # TODO: check version
#         try:
#             kind = config["kind"]
#             name = config["metadata"]["name"]
#             spec = config["spec"]
#         except KeyError:
#             self.logger.error("Bad config/spec, could not apply: %s", config)
#             return

#         namespace = self.default_namespace
#         if kind in ["Registry", "DataManager"]:
#             namespace = self.namespace
#             config["metadata"]["namespace"] = namespace
#         elif "namespace" in config["metadata"]:
#             namespace = config["metadata"]["namespace"]

#         # add broker if missing
#         try:
#             broker = config["spec"]["broker"]
#         except KeyError:
#             config["spec"]["broker"] = self.config["spec"]["broker"]

#         if namespace not in self.system_map:
#             self.system_map[namespace] = dict()

#         if kind not in self.system_map[namespace]:
#             self.system_map[namespace][kind] = dict()

#         self.system_map[namespace][kind][name] = {"id": None, "config": config, "status": None}

#     async def monitor_loop(self):

#         while True:

#             for ns, ns_system in self.system_map.items():
#                 for kind, kind_system in ns_system.items():
#                     for name, system in kind_system.items():
#                         try:
#                             config = system["config"]
#                             status = system["status"]
#                             if status is None:
#                                 self.logger.debug(
#                                     "monitor_loop: create %s-%s-%s", ns, kind, name
#                                 )

#                                 # check if service is started locally
#                                 part_of = None
#                                 try:
#                                     part_of = config["metadata"]["labels"]["part-of"]
#                                 except KeyError:
#                                     pass

#                                 if part_of:
#                                     try:
#                                         # part_of = config["metadata"]["labels"][
#                                         #     "part-of"
#                                         # ]
#                                         self.logger.debug("send message to %s", part_of)

#                                         # check to see if "part-of" resource exists
#                                         po_ns = config["metadata"]["namespace"]
#                                         po_kind = part_of["kind"]
#                                         po_name = part_of["name"]

#                                         if po := (
#                                             self.system_map[po_ns][po_kind][po_name]
#                                         ):
#                                             if po["id"]:
#                                                 # crate manage message for owner to create resource
#                                                 data = {
#                                                     envdsEvent.TYPE_MANAGE: {
#                                                         self.MANAGE_APPLY: config
#                                                     }
#                                                 }
#                                                 message = self.create_manage_request(
#                                                     data=data, target=po["id"]
#                                                 )
#                                                 await self.send_message(message)
#                                                 self.system_map[ns][kind][name]["status"] = Status()
#                                     except KeyError:
#                                         pass
#                                 else:
#                                     # if kind == "DAQSystem" or kind == "Registry":
#                                     #     # service = await self.add_service(config)
#                                     await self.create_resource(config=config)
#                                     self.system_map[ns][kind][name]["status"] = Status()
#                                 # else:
#                                 #     self.logger.debug("send message to part-of")

#                             elif not status.ready():
#                                 # TODO: start timer on object to manage fix
#                                 # if timeout, remove and try again.
#                                 pass
#                         except KeyError:
#                             self.logger.error(
#                                 "bad config/status: %s-%s-%s", ns, kind, name
#                             )
#             self.logger.debug(
#                 "monitor_loop: time until next check = %s", time_to_next(5)
#             )
#             await asyncio.sleep(time_to_next(5))  # what's the right time here? 1, 5?
#             # await asyncio.sleep(5)  # what's the right time here? 1, 5?

#         # self.envds_id = ".".join([self.envds_id, "system"])
#         # self.service_map = dict()

#         # # set message defaults
#         # # if not Message.default_message_types:
#         # self.default_message_types = [
#         #     # envdsEvent.TYPE_DATA,
#         #     envdsEvent.TYPE_MANAGE,
#         #     envdsEvent.TYPE_STATUS,
#         #     envdsEvent.TYPE_CONTROL,
#         #     # envdsEvent.TYPE_REGISTRY,
#         #     envdsEvent.TYPE_DISCOVERY,
#         # ]
#         # Message.set_default_types(self.default_message_types)

#         # # if not Message.default_message_type_actions:
#         # self.default_type_actions = [
#         #     envdsEvent.TYPE_ACTION_UPDATE,
#         #     envdsEvent.TYPE_ACTION_REQUEST,
#         #     envdsEvent.TYPE_ACTION_DELETE,
#         #     envdsEvent.TYPE_ACTION_SET,
#         # ]
#         # Message.set_default_type_actions(self.default_type_actions)

#         # self.default_subscriptions = []
#         # # self.default_subscriptions.append(f"{self.get_id()}.+.request")
#         # self.default_subscriptions.append(
#         #     f"{self.get_id()}.{envdsEvent.TYPE_CONTROL}.request"
#         # )
#         # self.default_subscriptions.append(
#         #     f"{self.get_id()}.{envdsEvent.TYPE_DISCOVERY}.request"
#         # )
#         # self.default_subscriptions.append(
#         #     f"{self.get_id()}.{envdsEvent.TYPE_MANAGE}.request"
#         # )
#         # self.default_subscriptions.append(
#         #     f"{self.get_id()}.{envdsEvent.TYPE_STATUS}.request"
#         # )

#         # self.setup()
#         # if "message_broker" in config:
#         #     mb_config = config["message_broker"]
#         #     self.loop.create_task(self.add_message_broker(config=mb_config))
#         # else:
#         #     self.logger.error("No message broker configured")
#         #     self.do_run = False
#         #     return

#         # add required services: registry, ?
#         # required services - registry should go first

#         # self.loop.create_task(self.create_required_services())
#         # registry_config = {
#         #     "type": "service",
#         #     "name": "registry",
#         #     # "namespace": "acg",
#         #     "instance": {
#         #         "module": "envds.registry.registry",
#         #         "class": "envdsRegistry",
#         #     },
#         #     "part-of": self.envds_id
#         # }
#         # self.loop.create_task(self.add_service(service_config=registry_config))

#     def set_config(self, config=None):
#         return super().set_config(config=config)

#     def handle_config(self, config=None):
#         return super().handle_config(config=config)

#     async def setup(self):
#         await super().setup()

#         # while not self.status.ready(type=Status.TYPE_CREATE):
#         #     self.logger.debug("waiting to create DataSystemManager")
#         #     await asyncio.sleep(1)
#         # await self.create_manager()

#         # start health monitor loop
#         self.loop.create_task(self.monitor_loop())

#         # setup health monitoring
#         #   subscribe to status channels for all objects
#         self.loop.create_task(self.run())

#     def apply_config(self, config=None):
#         if not config:
#             return

#         # await self.create_message_client(config=broker_config)

#     def set_config(self, config=None):
#         self.use_namespace = False
#         return super().set_config(config=config)

#     # async def message_handler(self):
#     #     pass

#     # async def create_required_services(self):

#     #     registry_config = {
#     #         "type": "service",
#     #         "name": "registry",
#     #         # "namespace": "acg",
#     #         "instance": {
#     #             "module": "envds.registry.registry",
#     #             "class": "envdsRegistry",
#     #         },
#     #         "part-of": self.get_id(),
#     #     }
#     #     await self.add_service(service_config=registry_config)

#     async def handle_status(self, message, extra=dict()):

#         if (action := Message.get_type_action(message)) :

#             if action == envdsEvent.TYPE_ACTION_UPDATE:
#                 id = message["source"]
#                 data = message.data
#                 try:
#                     ns = data["namespace"]
#                     kind = data["kind"]
#                     name = data["name"]
#                     status = data["status"]

#                     self.system_map[ns][kind][name]["id"] = id
#                     self.system_map[ns][kind][name]["status"].from_json(status)
#                 except KeyError:
#                     pass
#                 # self.refresh_registration_by_id(id)

#     async def handle_control(self, message, extra=dict()):
#         pass
#         return
#         if (action := Message.get_type_action(message)) :

#             if action == envdsEvent.TYPE_ACTION_REQUEST:
#                 data = message.data
#                 if "run" in data:
#                     try:
#                         control = data["run"]["type"]
#                         value = data["run"]["value"]
#                         if control == "shutdown" and value:
#                             await self.shutdown()
#                     except KeyError:
#                         self.logger("invalid run control message")
#                         pass

#                     # begin shutting down system
#                     # self.logger.info("shutdown requested")
#                     # extra = {"channel": "evnds/system/request"}
#                     # request = Message.create(
#                     #     source=self.envds_id,
#                     #     type=envdsEvent.TYPE_ACTION_REQUEST,
#                     #     data=data,
#                     #     **extra,
#                     # )
#                     # await self.shutdown()

#     # async def add_message_broker(self, config=None, **kwargs):
#     #     if not config:
#     #         return

#     #     try:
#     #         mod_ = importlib.import_module(config["instance"]["module"])
#     #         cls_ = getattr(mod_, config["instance"]["class"])
#     #         self.message_client = cls_(config=config, **kwargs)
#     #         self.logger.debug("new message client %s", self.message_client)
#     #     except Exception as e:
#     #         self.logger.error("%s: could not instantiate service: %s", e, config)

#     # async def add_service(
#     #     self, service_config=None, include_message_broker=True, **kwargs
#     # ):
#     #     if not service_config or service_config["type"] != "service":
#     #         return

#     #     if include_message_broker:
#     #         try:
#     #             mb_config = service_config["message_broker"]
#     #         except KeyError:
#     #             service_config["message_broker"] = self.config["message_broker"]

#     #     try:
#     #         mod_ = importlib.import_module(service_config["instance"]["module"])
#     #         cls_ = getattr(mod_, service_config["instance"]["class"])
#     #         self.service_map[service_config["name"]] = cls_(
#     #             config=service_config, **kwargs
#     #         )
#     #         service_id = cls_.get_id()
#     #         # prefix = self.message_client.to_channel(cls_.envds_id)
#     #         # TODO: check cls_ for what types we should subscribe to. For now, all
#     #         self.apply_subscription(".".join([service_id, "+", "update"]))
#     #     except Exception as e:
#     #         self.logger.error(
#     #             "%s: could not instantiate service: %s", e, service_config["name"]
#     #         )

#     def create_control_request(self, data=None, **kwargs):
#         # self.logger.debug("%s", sys.path)
#         type = envdsEvent.TYPE_CONTROL
#         action = envdsEvent.TYPE_ACTION_REQUEST
#         return self.create_message(type=type, action=action, data=data, **kwargs)

#     def create_manage_request(self, data=None, target=None, **kwargs):
#         # self.logger.debug("%s", sys.path)
#         type = envdsEvent.TYPE_MANAGE
#         action = envdsEvent.TYPE_ACTION_REQUEST
#         return self.create_message(
#             type=type, action=action, data=data, target=target, **kwargs
#         )

#     async def run(self):

#         # set status to creating
#         self.status.event(
#             StatusEvent.create(
#                 type=Status.TYPE_RUN,
#                 state=Status.STATE_RUNSTATE,
#                 status=Status.STARTING,
#                 ready_status=Status.RUNNING,
#             )
#         )

#         # wait for message_client to be instatiated or fail
#         # timeout = 10  # seconds
#         # secs = 0
#         # while not self.message_client:
#         #     if secs >= timeout:
#         #         self.logger.error(
#         #             "PANIC: could not create message client. Check config"
#         #         )
#         #         return
#         #     secs += 1
#         #     await asyncio.sleep(1)
#         # if not await self.wait_for_message_client():
#         #     self.do_run = False

#         # if self.do_run:
#         # self.apply_subscriptions(self.default_subscriptions)

#         # remove for debug
#         # start required services
#         # await self.create_required_services()

#         # if "services" in self.config:
#         #     for name, svc in self.config["services"].items():
#         #         await self.add_service(svc)

#         while not self.status.ready(type=Status.TYPE_CREATE):
#             self.logger.debug("waiting for startup")
#             await asyncio.sleep(1)

#         self.status.event(
#             StatusEvent.create(
#                 type=Status.TYPE_RUN,
#                 state=Status.STATE_RUNSTATE,
#                 status=Status.RUNNING,
#             )
#         )

#         do_shutdown_req = False
#         while self.do_run:
#             # extra = {"channel": "envds/system/status"}
#             # status = Message.create(
#             #     source=self.envds_id,
#             #     type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
#             #     data={"update": "ping"},
#             #     **extra,
#             # )
#             # if get_datetime().second % 10 == 0:

#             #     status = self.create_status_update(data=self.status.to_dict())
#             #     # status = self.create_status_update(
#             #     #     {"status": {"time": get_datetime_string(), "value": "OK"}}
#             #     # )
#             #     await self.send_message(status)
#             #     # do_shutdown_req = True
#             # # self.loop.create_task(self.send_message(status))

#             await asyncio.sleep(time_to_next(1))
#             # if do_shutdown_req:
#             #     # self.request_shutdown()
#             #     do_shutdown_req = False

#         self.logger.info("envDS shutdown.")
#         self.run_status = "SHUTDOWN"
#         # return await super().run()

#     async def shutdown(self):

#         if (
#             self.status.get_current_status(
#                 type=Status.TYPE_SHUTDOWN, state=Status.STATE_SHUTDOWN
#             )
#             != Status.SHUTTINGDOWN
#         ):

#             self.status.event(
#                 StatusEvent.create(
#                     type=Status.TYPE_SHUTDOWN,
#                     state=Status.STATE_SHUTDOWN,
#                     status=Status.SHUTTINGDOWN,
#                     ready_status=Status.SHUTDOWN,
#                 )
#             )

#             await self.shutdown_resources()

#             # # send shutdown request to all resources
#             # for kind, kind_map in self.resource_map.items():
#             #     for name, resource in kind_map.items():
#             #         self.logger.debug(
#             #             "shutdown resource: %s: %s -- %s", kind, name, resource
#             #         )
#             #         self.logger.debug("  resource_id: %s", resource.get_id())

#             # # send shutdown command to listening services
#             # message = self.create_control_request(
#             #     data={"run": {"type": "shutdown", "value": True}}
#             # )
#             # await self.send_message(message)

#             # give a moment to let message propogate
#             await asyncio.sleep(2)

#             # TODO: make timeout a higher level variable
#             timeout = 15
#             sec = 0
#             wait = True
#             # wait for services in service_map to finish shutting down
#             while sec <= timeout and wait:
#                 # wait = False
#                 if await self.check_resources_ready(type=Status.TYPE_SHUTDOWN):
#                     break
#                 # for name, service in self.service_map.items():
#                 #     if service.run_status != "SHUTDOWN":
#                 #         wait = True
#                 #         break
#                 sec += 1
#                 await asyncio.sleep(1)

#             self.status.event(
#                 StatusEvent.create(
#                     type=Status.TYPE_SHUTDOWN,
#                     state=Status.STATE_SHUTDOWN,
#                     status=Status.SHUTDOWN,
#                 )
#             )
#             # while not self.status.ready():
#             #     self.logger.debug("waiting to finish shutdown")
#             #     await asyncio.sleep(1)

#             while not self.status.ready(type=Status.TYPE_SHUTDOWN):
#                 self.logger.debug("waiting to finish shutdown")
#                 await asyncio.sleep(1)

#             self.do_run = False
#             return await super().shutdown()

#     def request_shutdown(self):
#         type = envdsEvent.TYPE_CONTROL
#         action = envdsEvent.TYPE_ACTION_REQUEST
#         data = {"run": {"type": "shutdown", "value": True}}
#         message = self.create_message(type=type, action=action, data=data)
#         self.loop.create_task(self.send_message(message))

        # self.loop
        # self.do_run = False

# end comment

class DataSystem(envdsBase):
    STATUS_STATE_REGISTRY = "registry"
    STATUS_STATE_MANAGER = "manager"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # these will override config
        # self.name = "envds-system"
        self.kind = "DAQSystem"
        self.envds_id = ".".join([self.app_sig, "system", self.name])
        self.use_namespace = False
        self.namespace = "envds"

    # start comment 

    #     self.manager = None
    #     # create message client
    #     # self.start_message_client()

    #     self.default_message_types = [
    #         envdsEvent.TYPE_DATA,
    #         envdsEvent.TYPE_MANAGE,
    #         envdsEvent.TYPE_STATUS,
    #         envdsEvent.TYPE_CONTROL,
    #         envdsEvent.TYPE_REGISTRY,
    #         envdsEvent.TYPE_DISCOVERY,
    #         envdsEvent.TYPE_RUNSTATE,
    #     ]
    #     Message.set_default_types(self.default_message_types)

    #     # if not Message.default_message_type_actions:
    #     self.default_type_actions = [
    #         envdsEvent.TYPE_ACTION_UPDATE,
    #         envdsEvent.TYPE_ACTION_REQUEST,
    #         envdsEvent.TYPE_ACTION_DELETE,
    #         envdsEvent.TYPE_ACTION_SET,
    #         envdsEvent.TYPE_ACTION_RESPONSE,
    #     ]
    #     Message.set_default_type_actions(self.default_type_actions)

    #     self.loop.create_task(self.setup())
    #     self.do_run = True

    # def set_config(self, config=None):
    #     return super().set_config(config=config)

    # def handle_config(self, config=None):
    #     return super().handle_config(config=config)

    # async def setup(self):
    #     await super().setup()

    #     while not self.status.ready(type=Status.TYPE_CREATE):
    #         self.logger.debug("waiting to create DataSystemManager")
    #         await asyncio.sleep(1)

    #     await self.create_manager()
    #     await self.create_registry()

    # async def create_registry(self, config=None):
    #     # TODO: allow config param to override?

    #     self.logger.debug("creating Registry")

    #     # set status to creating
    #     # self.status.event(
    #     #     StatusEvent.create(
    #     #         type=Status.TYPE_CREATE,
    #     #         state=self.STATUS_STATE_REGISTRY,
    #     #         status=Status.CREATING,
    #     #         ready_status=Status.CREATED,
    #     #     )
    #     # )

    #     reg_config = {
    #         "apiVersion": "envds/v1",
    #         "kind": "Registry",
    #         "metadata": {
    #             "name": "who-daq",  # <- this has to be unique name in namespace
    #             "namespace": "envds",
    #             # "part-of": {"kind": "DataSystem", "name": "who-daq"},
    #         },
    #         "spec": {
    #             "class": {
    #                 "module": "envds.registry.registry",
    #                 "class": "envdsRegistry",
    #             },
    #         },
    #     }

    #     await self.manager.apply(config=reg_config)
    #     # registry_config = dict()
    #     # for key, val in self.config.items():
    #     #     if key == "kind":
    #     #         registry_config[key] = "Registry"
    #     #     elif key == "metadata":
    #     #         # manager_config[key] = {"name": "envds-manager", "namespace": "envds"}
    #     #         registry_config[key] = {"name": self.name, "namespace": "envds"}
    #     #     else:
    #     #         registry_config[key] = val

    #     # self.registry = envdsRegistry(config=registry_config)
    #     # self.registry = envdsRegistry(config=registry_config)
    #     # if self.registry:

    #     #     # set status to created
    #     #     self.status.event(
    #     #         StatusEvent.create(
    #     #             type=Status.TYPE_CREATE,
    #     #             state=self.STATUS_STATE_REGISTRY,
    #     #             status=Status.CREATED,
    #     #         )
    #     #     )
    #     pass

    # async def create_manager(self, config=None):
    #     # TODO: allow config param to override?

    #     self.logger.debug("creating DataSystemManager client")

    #     # set status to creating
    #     self.status.event(
    #         StatusEvent.create(
    #             type=Status.TYPE_CREATE,
    #             state=self.STATUS_STATE_MANAGER,
    #             status=Status.CREATING,
    #             ready_status=Status.CREATED,
    #         )
    #     )
    #     manager_config = dict()
    #     for key, val in self.config.items():
    #         if key == "kind":
    #             manager_config[key] = "DataSystemManager"
    #         elif key == "metadata":
    #             # manager_config[key] = {"name": "envds-manager", "namespace": "envds"}
    #             manager_config[key] = {"name": self.name, "namespace": "envds"}
    #         else:
    #             manager_config[key] = val

    #     self.manager = DataSystemManager(config=manager_config)
    #     if self.manager:

    #         # set status to created
    #         self.status.event(
    #             StatusEvent.create(
    #                 type=Status.TYPE_CREATE,
    #                 state=self.STATUS_STATE_MANAGER,
    #                 status=Status.CREATED,
    #             )
    #         )

    # async def apply(self, config=None):
    #     if config is None:
    #         return

    #     while not self.status.ready(type=Status.TYPE_CREATE):
    #         self.logger.debug("waiting for startup")
    #         await asyncio.sleep(1)

    #     await self.manager.apply(config)

    # def apply_nowait(self, config=None):
    #     self.loop.create_task(self.apply(config=config))

    # async def run(self):

    #     # set status to creating
    #     self.status.event(
    #         StatusEvent.create(
    #             type=Status.TYPE_RUN,
    #             state=Status.STATE_RUNSTATE,
    #             status=Status.STARTING,
    #             ready_status=Status.RUNNING,
    #         )
    #     )

    #     # this part is bootstrapping...need special case for these
    #     # wait for system to become ready
    #     # await self.ready_to_run() or something like that
    #     # if timeout, fail.

    #     # create DataSystemMananger
    #     # wait of mananger to become ready
    #     # manager.ready_to_run
    #     # if timeout, fail

    #     while not self.status.ready(type=Status.TYPE_CREATE):
    #         self.logger.debug("waiting for startup")
    #         await asyncio.sleep(1)

    #     self.status.event(
    #         StatusEvent.create(
    #             type=Status.TYPE_RUN,
    #             state=Status.STATE_RUNSTATE,
    #             status=Status.RUNNING,
    #         )
    #     )

    #     do_shutdown_req = False
    #     shutdown_requested = False
    #     while self.do_run:

    #         if get_datetime().second % 10 == 0:

    #             # # status_event = StatusEvent.create(
    #             # #     type=Status.TYPE_RUN,
    #             # #     state=Status.STATE_RUNSTATE,
    #             # #     status=Status.RUNNING,
    #             # # )
    #             # # self.status.event(status_event)

    #             # status = self.create_status_update(data=self.status.to_dict())
    #             # # status = self.create_status_update(
    #             # #     {"status": {"time": get_datetime_string(), "value": "OK"}}
    #             # # )
    #             # await self.send_message(status)
    #             do_shutdown_req = True
    #         # self.loop.create_task(self.send_message(status))
    #         if do_shutdown_req and not shutdown_requested:
    #             # self.request_shutdown()
    #             shutdown_requested = True
    #             do_shutdown_req = False

    #         await asyncio.sleep(time_to_next(1))

    # async def shutdown(self):
    #     await self.manager.shutdown()
    #     # await self.registry.shutdown()
    #     # while not self.manager.status.ready():
    #     #     self.logger.debug("waiting for SystemManager to shutdown")
    #     #     await asyncio.sleep(1)
    #     # wait for status to become ready
    #     await super().shutdown()
    #     self.do_run = False

    # def request_shutdown(self):
    #     # type = envdsEvent.TYPE_CONTROL
    #     # action = envdsEvent.TYPE_ACTION_REQUEST
    #     # data = {"run": {"type": "shutdown", "value": True}}
    #     # message = self.create_message(type=type, action=action, data=data)
    #     # self.loop.create_task(self.send_message(message))
    #     self.loop.create_task(self.shutdown())
    #     # self.loop
    #     # self.do_run = False

    # end comment
    
# def run():
#     event_loop = asyncio.get_running_loop()

async def main(**kwargs):

    event_loop = asyncio.get_running_loop()

    # configure logging to stdout
    # isofmt = "%Y-%m-%dT%H:%M:%SZ"
    isofmt = get_datetime_format()
    # isofmt = get_datetime_format(fraction=True)
    logger = logging.getLogger()
    # root_logger.setLevel(logging.DEBUG)
    logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # envds = DataSystem()
    envds = None

    def shutdown_handler(*args):
        envds.request_shutdown()

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    logger.debug("main: Started")


if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )
    # parser.add_argument("-h", "--host", help="set api host address")
    # parser.add_argument("-p", "--port", help="set api port number")
    # parser.add_argument("-n", "--name", help="set DataSystem name")

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    kwargs = dict()

    log_level = logging.INFO
    if cl_args.log_level:
        level = cl_args.log_level
        if level == "WARN":
            log_level = logging.WARN
        elif level == "ERROR":
            log_level = logging.ERROR
        elif log_level == "DEBUG":
            log_level = logging.DEBUG
        elif log_level == "CRITICAL":
            log_level = logging.CRITICAL

    if cl_args.debug:
        log_level = logging.DEBUG

    kwargs["log_level"] = log_level

    # if cl_args.host:
    #     kwargs["host"] = cl_args.host
    
    # if cl_args.port:
    #     kwargs["port"] = cl_args.port

    # if cl_args.name:
    #     kwargs["name"] = cl_args.name


    # set path
    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    # from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    # # from managers.hardware_manager import HardwareManager
    # # from envds.eventdata.eventdata import EventData
    # # from envds.eventdata.broker.broker import MQTTBroker

    asyncio.run(main(**kwargs))
    sys.exit()

    # # configure logging to stdout
    # isofmt = "%Y-%m-%dT%H:%M:%SZ"
    # # isofmt = get_datetime_format(fraction=True)
    # root_logger = logging.getLogger()
    # # root_logger.setLevel(logging.DEBUG)
    # root_logger.setLevel(log_level)
    # handler = logging.StreamHandler(sys.stdout)
    # formatter = logging.Formatter(
    #     "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    # )
    # handler.setFormatter(formatter)
    # root_logger.addHandler(handler)

    # event_loop = asyncio.get_event_loop()

    config = {
        # "namespace": "gov.noaa.pmel.acg",
        "message_broker": {
            "client": {
                "instance": {
                    "module": "envds.message.message",
                    "class": "MQTTBrokerClient",
                }
            },
            "config": {
                "host": "localhost",
                "port": 1883,
                # "keepalive": 60,
                "ssl_context": None,
                # "ssl_client_cert": None,
                # ne
            },
        },
    }

    # add services
    # services =
    #     [
    #         {
    #             "type": "service",
    #             "name": "datamanager",
    #             "namespace": "acg",
    #             "instance": {
    #                 "module": "envds.datamanager.datamanager",
    #                 "class": "envdsDataManager",
    #             },
    #         },
    #         {
    #             "type": "service",
    #             "name": "testdaq",
    #             "namespace": "acg",
    #             "instance": {"module": "envds.daq", "class": "envdsDAQ"},
    #         },
    #     ]

    envds = DataSystemManager(config=config)

    # create the DAQManager
    # daq_manager = DAQManager().configure(config=config)
    # if namespace is specified
    # daq_manager.set_namespace("junge")
    # daq_manager.set_msg_broker()
    # daq_manager.start()

    # task = event_loop.create_task(daq_manager.run())
    # task_list = asyncio.all_tasks(loop=event_loop)

    event_loop.add_signal_handler(signal.SIGINT, envds.request_shutdown)
    event_loop.add_signal_handler(signal.SIGTERM, envds.request_shutdown)

    event_loop.run_until_complete(envds.run())

    # try:
    #     event_loop.run_until_complete(daq_manager.run())
    # except KeyboardInterrupt:
    #     root_logger.info("Shutdown requested")
    #     event_loop.run_until_complete(daq_manager.shutdown())
    #     event_loop.run_forever()

    # finally:
    #     root_logger.info("Closing event loop")
    #     event_loop.close()

    # # from daq.manager.sys_manager import SysManager
    # # from daq.controller.controller import ControllerFactory  # , Controller
    # # from client.wsclient import WSClient
    # # import shared.utilities.util as util
    # # from shared.data.message import Message
    # # from shared.data.status import Status
    # # from shared.data.namespace import Namespace

