import abc
import sys
import getopt
import argparse
import os
import asyncio
import signal
import logging
import importlib

from envds.status.status import Status, StatusMonitor, StatusEvent
from envds.message.message import Message
from envds.message.broker.client import MessageBrokerClientFactory
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    time_to_next,
)


class envdsEvent:

    APP_PREFIX = "envds"

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
    TYPE_ACTION_SET = "set"
    TYPE_ACTION_GET = "get"
    TYPE_ACTION_INSERT = "insert"
    TYPE_ACTION_BROADCAST = "broadcast"

    @staticmethod
    def get_type(type=TYPE_DATA, action=TYPE_ACTION_UPDATE):
        return ".".join([envdsEvent.APP_PREFIX, type, action])


class envdsBase(abc.ABC):
    STATUS_STATE_MSGCLIENT = "message-client"

    STATUS_CREATING = "creating"
    STATUS_CREATED = "created"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__()

        self.loop = asyncio.get_event_loop()

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug("Starting %s", self.__class__.__name__)

        self.status = StatusMonitor().get_status()
        self.status_update_freq = 10

        self.app_sig = "envds"
        self.default_namespace = "default"

        # these need to be set by instantiated objects:
        self.name = None
        self.envds_id = None

        self.use_namespace = True  # most things should be namespaced
        self.namespace = None

        self.config = dict()
        if config:
            # each object should handle their own config.
            #   - broker will be handled by base class
            self.handle_config(config)

        self.message_client = None
        self.subscriptions = dict()

        # self.logger.debug("path: %s", sys.path)

        self.send_buffer = asyncio.Queue()
        self.rec_buffer = asyncio.Queue()
        self.buffer_tasks = []

        self.resource_map = dict()

        # self.start_message_buffers()

        # self.config = config

        # ----

        # self.use_namespace = True
        # self.namespace = "default"
        # self.envds_id = "envds"

        # self.set_config(config)
        # # self.config = config
        # # self.message_broker_config = None

        # mb_created = False
        # # self.add_message_broker()
        # self.loop.create_task(self.add_message_broker())
        # # if "message_broker" in config:
        # #     mb_config = config["message_broker"]
        # #     self.loop.create_task(self.add_message_broker(config=mb_config))
        # # else:
        # #     self.logger.error("No message broker configured")
        # #     self.do_run = False
        # #     return

        # self.do_run = True
        # self.run_status = "STARTING"  # "RUNNING", "SHUTDOWN"

        # new
        # start message broker client
        # pass Namespace to ConfigManager
        # start ConfigManager (or whatever)
        # ready to start adding services, etc

    # @abc.abstractmethod
    # def get_namespace(self):
    #     pass

    # @abc.abstractmethod
    # def get_id(self):
    #     pass

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
        self.loop.create_task(self.update_status_loop())

    async def check_for_ready(self):

        while True:
            ready = True
            for condition in self.ready_conditions:
                if not condition.result():
                    self.check_ready_flag = False

            self.check_ready_flag = True
            asyncio.sleep(1)

    # def create_message_client(self, config=None):
    #     self.loop.create_task(self._create_message_client(config=config))
    # TODO: set status to indicate resource being created
    async def create_resource(self, config, include_message_broker=True, **kwargs):
        if config is None:
            return

        # verify config
        if "kind" in config and "metadata" in config and "spec" in config:
            pass
        else:
            self.logger.error("create_object: bad config: %s", config)

        if include_message_broker:
            try:
                # mb_config = config["message_broker"]
                mb_config = config["spec"]["broker"]
            except KeyError:
                self.logger.info("create_object: adding default broker")
                config["spec"]["broker"] = self.config["broker"]

        # delete resource if exists - TODO: should call delete_resource
        try:
            resource = self.resource_map[config["kind"]][config["name"]]
            if resource:
                await resource.shutdown()
            self.resource_map[config["kind"]][config["name"]] = None
        except KeyError:
            pass

        try:
            mod_name = config["spec"]["class"]["module"]
            # mod_ = importlib.import_module(config["instance"]["module"])
            mod_ = importlib.import_module(mod_name)
            class_name = config["spec"]["class"]["class"]
            # cls_ = getattr(mod_, config["instance"]["class"])
            cls_ = getattr(mod_, class_name)

            kind = config["kind"]
            name = config["metadata"]["name"]
            if kind not in self.resource_map:
                self.resource_map[kind] = dict()
            # if config["kind"] not in self.resource_map:
            #     self.resource_map[config["kind"]] = dict()
            self.resource_map[kind][name] = cls_(
                config=config, **kwargs
            )
            # self.resource_map[config["kind"]][config["metadata"]["name"]] = cls_(
            #     config=config, **kwargs
            # )
            # resource_id = cls_.get_id()
            # prefix = self.message_client.to_channel(cls_.envds_id)
            # TODO: check cls_ for what types we should subscribe to. For now, all
            # self.apply_subscription(".".join([resource_id, "+", "update"]))
        except Exception as e:
            self.logger.error(
                "%s: could not instantiate service: %s", e, config["name"]
            )

        return None

    async def stop_message_client(self):
        if self.message_client:
            # await self.message_client.stop()
            pass

    async def create_message_client(self, config=None):
        self.logger.debug("creating message client")

        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_CREATE,
                state=self.STATUS_STATE_MSGCLIENT,
                status=self.STATUS_CREATING,
                ready_status=self.STATUS_CREATED,
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
                        status=self.STATUS_CREATED,
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

        self.buffer_tasks.append(self.loop.create_task(self.send_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.rec_message_loop()))
        self.buffer_tasks.append(self.loop.create_task(self.message_handler()))

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

    async def add_message_broker(self, **kwargs):
        if not self.config:
            self.logger.error("could not instantiate message broker: missing config")
            return

        try:
            self.message_client = kwargs["message_broker_client"]
            self.logger.info("message client added: %s", self.message_client)
            return
        except KeyError:
            pass

        mb_config = None
        if "message_broker" in self.config:
            mb_config = self.config["message_broker"]
        elif self.message_broker_config:
            mb_config = self.message_broker_config

        if mb_config:
            try:
                mod_ = importlib.import_module(
                    mb_config["client"]["instance"]["module"]
                )
                cls_ = getattr(mod_, mb_config["client"]["instance"]["class"])
                self.message_client = cls_(config=mb_config, **kwargs)
                self.logger.info("message client added: %s", self.message_client)
            except Exception as e:
                self.logger.error(
                    "could not instantiate message broker: %s. config: %s", e, mb_config
                )
                self.message_client = None

    def apply_subscriptions(self, subscriptions):
        if subscriptions:
            self.loop.create_task(
                self.message_client.subscribe_channel_list(subscriptions)
            )

    def apply_subscription(self, channel):
        if channel:
            self.loop.create_task(self.message_client.subscribe_channel(channel))

    # create message helper functions
    def create_message(self, type=None, action=None, data=None, **kwargs):
        if not type or not action:
            return None

        # set default channel using envds_id+action if missing from kwargs
        try:
            channel = kwargs["channel"]
        except KeyError:
            if self.message_client:
                kwargs["channel"] = "/".join(
                    [self.message_client.to_channel(self.get_id()), type, action]
                )

        msg_type = ".".join([envdsEvent.APP_PREFIX, type, action])
        return Message.create(source=self.get_id(), type=msg_type, data=data, **kwargs)

    async def update_status_loop(self):

        while not self.status.ready(type=Status.TYPE_CREATE):
            self.logger.debug("update_status_loop: waiting for startup")
            await asyncio.sleep(1)

        while True:
            status = self.create_status_update(data=self.status.to_dict())
            await self.send_message(status)
            await asyncio.sleep(self.status_update_freq)

    def create_status_update(self, data=None, **kwargs):
        # self.logger.debug("%s", sys.path)
        type = envdsEvent.TYPE_STATUS
        action = envdsEvent.TYPE_ACTION_UPDATE
        return self.create_message(type=type, action=action, data=data, **kwargs)

    # def create_data_message(
    #     self, action=envdsEvent.TYPE_ACTION_UPDATE, data=None, **kwargs
    # ):
    #     event_type = ".".join([envdsEvent.TYPE_DATA, action])
    #     return Message.create(
    #         source=self.get_id(), type=event_type, data=data, **kwargs
    #     )

    async def message_handler(self):
        """
        Parse/unbundle data from message bus. This assumes a standard format where 
        data = {"message": message, "key": "value"...}. This function will extract
        the message and send message and extra data to the router.
        """
        while True:
            data = await self.rec_buffer.get()
            try:
                message = data.pop("message")
                await self.route(message, extra=data)
            except (TypeError, KeyError):
                self.logger.warn(
                    "messages not in standard format, override 'message_handler'"
                )

    async def route(self, message, extra=dict()):
        # use event["type"] to do initial routing
        routing_table = {
            envdsEvent.TYPE_DATA: self.handle_data,
            envdsEvent.TYPE_STATUS: self.handle_status,
            envdsEvent.TYPE_CONTROL: self.handle_control,
            envdsEvent.TYPE_MANAGE: self.handle_manage,
            envdsEvent.TYPE_REGISTRY: self.handle_registry,
        }

        # routed = False
        self.logger.debug("Message defaults: %s", Message.default_message_types)
        try:
            fn = routing_table[Message.get_type(message)]
            await fn(message, extra=extra)
            return
        except KeyError:
            pass
        await self.handle(message, extra=extra)

        # for name, fn in routing_table.items():
        #     if name in message["type"].split("."):
        #         await fn(message, extra=extra)
        #         return
        # await self.handle(message, extra=extra)

    async def handle(self, message, extra=dict()):
        pass

    async def handle_data(self, message, extra=dict()):
        pass

    async def handle_status(self, message, extra=dict()):
        pass

    async def handle_control(self, message, extra=dict()):
        pass

    async def handle_manage(self, message, extra=dict()):
        pass

    async def handle_registry(self, message, extra=dict()):
        pass

    async def wait_for_message_client(self) -> bool:
        timeout = 10  # seconds
        secs = 0
        while not self.message_client:
            if secs >= timeout:
                self.logger.error(
                    "PANIC: could not create message client. Check config"
                )
                return False
            secs += 1
            await asyncio.sleep(1)
        return True

    async def run(self):

        self.run_status = "RUNNING"
        while self.do_run:

            await asyncio.sleep(1)

        self.run_status = "SHUTDOWN"

    @abc.abstractmethod
    async def shutdown(self):
        """
        Shutdown the base processes. Usually run this at end of derived methods
        in child classes
        """
        self.run_status = "SHUTDOWN"


class DataSystemManager(envdsBase):
    """
    Manager class that creates the platform/infrastructure to run the envds services. 
    """

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # # default/base namespace for envds
        # self.namespace = "envds"
        # namespace = { # envds namespace
        #     "apiVersion": "envds/v1",
        #     "kind": "Namespace",
        #     "metadata": {
        #         "name": self.namespace
        #     }
        # }
        # self.add_broker_client()
        # self.create_config_manager([namespace, self.config])

        # ----
        self.use_namespace = False
        self.namespace = "envds"
        self.name = "envds-manager"
        self.envds_id = ".".join([self.app_sig, "manager"])

        self.loop.create_task(self.setup())
        self.do_run = True

        self.service_map = dict()
        self.system_map = {
            # <namespace>: <kind>: <name> : {config}
            # "envds": {  # these really won't be used but it gives the template
            #     "DAQSystem": {"envds-system": {"config": "here", "status": "here"}},
            #     "DAQManager": {"envds-manager": {"config": "here"}},
            # }
        }

    async def apply(self, config=None):
        if config is None:
            return

        # TODO: check version
        try:
            kind = config["kind"]
            name = config["metadata"]["name"]
            spec = config["spec"]
        except KeyError:
            self.logger.error("Bad config/spec, could not apply: %s", config)
            return

        namespace = self.default_namespace
        if "namespace" in config["metadata"]:
            namespace = config["metadata"]["namespace"]

        # add broker if missing
        try:
            broker = config["spec"]["broker"]
        except KeyError:
            config["spec"]["broker"] = self.config["spec"]["broker"]

        if namespace not in self.system_map:
            self.system_map[namespace] = dict()

        if kind not in self.system_map[namespace]:
            self.system_map[namespace][kind] = dict()

        self.system_map[namespace][kind][name] = {"config": config, "status": None}

    async def monitor_loop(self):

        while True:

            for ns, ns_system in self.system_map.items():
                for kind, kind_system in ns_system.items():
                    for name, system in kind_system.items():
                        try:
                            config = system["config"]
                            status = system["status"]
                            if status is None:
                                self.logger.debug(
                                    "monitor_loop: create %s-%s-%s", ns, kind, name
                                )

                                # check if service is started locally
                                if kind == "DAQSystem":
                                    # service = await self.add_service(config)
                                    await self.create_resource(config=config)
                                    self.system_map[ns][kind][name]["status"] = Status()
                                else:
                                    self.logger.debug("send message to part-of")

                            elif not status.ready():
                                # TODO: start timer on object to manage fix
                                # if timeout, remove and try again.
                                pass
                        except KeyError:
                            self.logger.error(
                                "bad config/status: %s-%s-%s", ns, kind, name
                            )
            self.logger.debug(time_to_next(5))
            await asyncio.sleep(5)  # what's the right time here? 1, 5?

        # self.envds_id = ".".join([self.envds_id, "system"])
        # self.service_map = dict()

        # # set message defaults
        # # if not Message.default_message_types:
        # self.default_message_types = [
        #     # envdsEvent.TYPE_DATA,
        #     envdsEvent.TYPE_MANAGE,
        #     envdsEvent.TYPE_STATUS,
        #     envdsEvent.TYPE_CONTROL,
        #     # envdsEvent.TYPE_REGISTRY,
        #     envdsEvent.TYPE_DISCOVERY,
        # ]
        # Message.set_default_types(self.default_message_types)

        # # if not Message.default_message_type_actions:
        # self.default_type_actions = [
        #     envdsEvent.TYPE_ACTION_UPDATE,
        #     envdsEvent.TYPE_ACTION_REQUEST,
        #     envdsEvent.TYPE_ACTION_DELETE,
        #     envdsEvent.TYPE_ACTION_SET,
        # ]
        # Message.set_default_type_actions(self.default_type_actions)

        # self.default_subscriptions = []
        # # self.default_subscriptions.append(f"{self.get_id()}.+.request")
        # self.default_subscriptions.append(
        #     f"{self.get_id()}.{envdsEvent.TYPE_CONTROL}.request"
        # )
        # self.default_subscriptions.append(
        #     f"{self.get_id()}.{envdsEvent.TYPE_DISCOVERY}.request"
        # )
        # self.default_subscriptions.append(
        #     f"{self.get_id()}.{envdsEvent.TYPE_MANAGE}.request"
        # )
        # self.default_subscriptions.append(
        #     f"{self.get_id()}.{envdsEvent.TYPE_STATUS}.request"
        # )

        # self.setup()
        # if "message_broker" in config:
        #     mb_config = config["message_broker"]
        #     self.loop.create_task(self.add_message_broker(config=mb_config))
        # else:
        #     self.logger.error("No message broker configured")
        #     self.do_run = False
        #     return

        # add required services: registry, ?
        # required services - registry should go first

        # self.loop.create_task(self.create_required_services())
        # registry_config = {
        #     "type": "service",
        #     "name": "registry",
        #     # "namespace": "acg",
        #     "instance": {
        #         "module": "envds.registry.registry",
        #         "class": "envdsRegistry",
        #     },
        #     "part-of": self.envds_id
        # }
        # self.loop.create_task(self.add_service(service_config=registry_config))

    def set_config(self, config=None):
        return super().set_config(config=config)

    def handle_config(self, config=None):
        return super().handle_config(config=config)

    async def setup(self):
        await super().setup()

        while not self.status.ready(type=Status.TYPE_CREATE):
            self.logger.debug("waiting to create DataSystemManager")
            await asyncio.sleep(1)
        # await self.create_manager()

        # start health monitor loop
        self.loop.create_task(self.monitor_loop())

        # setup health monitoring
        #   subscribe to status channels for all objects
        self.loop.create_task(self.run())

    def apply_config(self, config=None):
        if not config:
            return

        # await self.create_message_client(config=broker_config)

    # def set_config(self, config=None):
    #     self.use_namespace = False
    #     return super().set_config(config=config)

    # async def message_handler(self):
    #     pass

    async def create_required_services(self):

        registry_config = {
            "type": "service",
            "name": "registry",
            # "namespace": "acg",
            "instance": {
                "module": "envds.registry.registry",
                "class": "envdsRegistry",
            },
            "part-of": self.get_id(),
        }
        await self.add_service(service_config=registry_config)

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

                    # begin shutting down system
                    # self.logger.info("shutdown requested")
                    # extra = {"channel": "evnds/system/request"}
                    # request = Message.create(
                    #     source=self.envds_id,
                    #     type=envdsEvent.TYPE_ACTION_REQUEST,
                    #     data=data,
                    #     **extra,
                    # )
                    # await self.shutdown()

    # async def add_message_broker(self, config=None, **kwargs):
    #     if not config:
    #         return

    #     try:
    #         mod_ = importlib.import_module(config["instance"]["module"])
    #         cls_ = getattr(mod_, config["instance"]["class"])
    #         self.message_client = cls_(config=config, **kwargs)
    #         self.logger.debug("new message client %s", self.message_client)
    #     except Exception as e:
    #         self.logger.error("%s: could not instantiate service: %s", e, config)

    async def add_service(
        self, service_config=None, include_message_broker=True, **kwargs
    ):
        if not service_config or service_config["type"] != "service":
            return

        if include_message_broker:
            try:
                mb_config = service_config["message_broker"]
            except KeyError:
                service_config["message_broker"] = self.config["message_broker"]

        try:
            mod_ = importlib.import_module(service_config["instance"]["module"])
            cls_ = getattr(mod_, service_config["instance"]["class"])
            self.service_map[service_config["name"]] = cls_(
                config=service_config, **kwargs
            )
            service_id = cls_.get_id()
            # prefix = self.message_client.to_channel(cls_.envds_id)
            # TODO: check cls_ for what types we should subscribe to. For now, all
            self.apply_subscription(".".join([service_id, "+", "update"]))
        except Exception as e:
            self.logger.error(
                "%s: could not instantiate service: %s", e, service_config["name"]
            )

    def create_control_update(self, data=None, **kwargs):
        # self.logger.debug("%s", sys.path)
        type = envdsEvent.TYPE_CONTROL
        action = envdsEvent.TYPE_ACTION_UPDATE
        return self.create_message(type=type, action=action, data=data, **kwargs)

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

        # wait for message_client to be instatiated or fail
        # timeout = 10  # seconds
        # secs = 0
        # while not self.message_client:
        #     if secs >= timeout:
        #         self.logger.error(
        #             "PANIC: could not create message client. Check config"
        #         )
        #         return
        #     secs += 1
        #     await asyncio.sleep(1)
        # if not await self.wait_for_message_client():
        #     self.do_run = False

        # if self.do_run:
        # self.apply_subscriptions(self.default_subscriptions)

        # remove for debug
        # start required services
        # await self.create_required_services()

        # if "services" in self.config:
        #     for name, svc in self.config["services"].items():
        #         await self.add_service(svc)

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

        do_shutdown_req = False
        while self.do_run:
            # extra = {"channel": "envds/system/status"}
            # status = Message.create(
            #     source=self.envds_id,
            #     type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
            #     data={"update": "ping"},
            #     **extra,
            # )
            # if get_datetime().second % 10 == 0:

            #     status = self.create_status_update(data=self.status.to_dict())
            #     # status = self.create_status_update(
            #     #     {"status": {"time": get_datetime_string(), "value": "OK"}}
            #     # )
            #     await self.send_message(status)
            #     # do_shutdown_req = True
            # # self.loop.create_task(self.send_message(status))

            await asyncio.sleep(time_to_next(1))
            # if do_shutdown_req:
            #     # self.request_shutdown()
            #     do_shutdown_req = False

        self.logger.info("envDS shutdown.")
        self.run_status = "SHUTDOWN"
        # return await super().run()

    async def shutdown(self):

        # send shutdown command to listening services
        message = self.create_control_update(
            data={"run": {"type": "shutdown", "value": True}}
        )
        await self.send_message(message)

        timeout = 15
        sec = 0
        wait = True
        # wait for services in service_map to finish shutting down
        while sec <= timeout and wait:
            wait = False
            for name, service in self.service_map.items():
                if service.run_status != "SHUTDOWN":
                    wait = True
                    break
            sec += 1
            await asyncio.sleep(1)
        self.do_run = False
        return await super().shutdown()

    def request_shutdown(self):
        type = envdsEvent.TYPE_CONTROL
        action = envdsEvent.TYPE_ACTION_REQUEST
        data = {"run": {"type": "shutdown", "value": True}}
        message = self.create_message(type=type, action=action, data=data)
        self.loop.create_task(self.send_message(message))

        # self.loop
        # self.do_run = False


class DataSystem(envdsBase):
    STATUS_STATE_MANAGER = "manager"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # these will override config
        self.name = "envds-system"
        self.envds_id = ".".join([self.app_sig, "system"])
        self.use_namespace = False
        self.namespace = "envds"

        self.manager = None
        # create message client
        # self.start_message_client()
        self.loop.create_task(self.setup())
        self.do_run = True

    def set_config(self, config=None):
        return super().set_config(config=config)

    def handle_config(self, config=None):
        return super().handle_config(config=config)

    async def setup(self):
        await super().setup()

        while not self.status.ready(type=Status.TYPE_CREATE):
            self.logger.debug("waiting to create DataSystemManager")
            await asyncio.sleep(1)
        await self.create_manager()

    async def create_manager(self, config=None):
        self.logger.debug("creating DataSystemManager client")

        # set status to creating
        self.status.event(
            StatusEvent.create(
                type=Status.TYPE_CREATE,
                state=self.STATUS_STATE_MANAGER,
                status=self.STATUS_CREATING,
                ready_status=self.STATUS_CREATED,
            )
        )
        manager_config = dict()
        for key, val in self.config.items():
            if key == "kind":
                manager_config[key] = "DataSystemManager"
            elif key == "metadata":
                manager_config[key] = {"name": "envds-manager", "namespace": "envds"}
            else:
                manager_config[key] = val

        self.manager = DataSystemManager(config=manager_config)
        if self.manager:

            # set status to created
            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_CREATE,
                    state=self.STATUS_STATE_MANAGER,
                    status=self.STATUS_CREATED,
                )
            )

    async def apply(self, config=None):
        if config is None:
            return

        while not self.status.ready(type=Status.TYPE_CREATE):
            self.logger.debug("waiting for startup")
            await asyncio.sleep(1)

        await self.manager.apply(config)

    def apply_nowait(self, config=None):
        self.loop.create_task(self.apply(config=config))

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

                # # status_event = StatusEvent.create(
                # #     type=Status.TYPE_RUN,
                # #     state=Status.STATE_RUNSTATE,
                # #     status=Status.RUNNING,
                # # )
                # # self.status.event(status_event)

                # status = self.create_status_update(data=self.status.to_dict())
                # # status = self.create_status_update(
                # #     {"status": {"time": get_datetime_string(), "value": "OK"}}
                # # )
                # await self.send_message(status)
                do_shutdown_req = True
            # self.loop.create_task(self.send_message(status))

            await asyncio.sleep(time_to_next(1))

    async def shutdown(self):
        return await super().shutdown()

    def request_shutdown(self):
        type = envdsEvent.TYPE_CONTROL
        action = envdsEvent.TYPE_ACTION_REQUEST
        data = {"run": {"type": "shutdown", "value": True}}
        message = self.create_message(type=type, action=action, data=data)
        self.loop.create_task(self.send_message(message))

        # self.loop
        self.do_run = False


if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

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

    # set path
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    # from managers.hardware_manager import HardwareManager
    # from envds.eventdata.eventdata import EventData
    # from envds.eventdata.broker.broker import MQTTBroker

    # configure logging to stdout
    isofmt = "%Y-%m-%dT%H:%M:%SZ"
    # isofmt = get_datetime_format(fraction=True)
    root_logger = logging.getLogger()
    # root_logger.setLevel(logging.DEBUG)
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    event_loop = asyncio.get_event_loop()

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

