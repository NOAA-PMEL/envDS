import asyncio
# import sys
from envds.system.envds import envdsBase, envdsEvent
from envds.message.message import Message
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    string_to_datetime,
    time_to_next,
)
from envds.status.status import Status, StatusEvent


class envdsRegistry(envdsBase):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.use_namespace = False
        self.kind = "Registry"
        # self.envds_id = ".".join([self.envds_id, "registry"])
        self.envds_id = ".".join([self.app_sig, "registry"])

        # self.default_subscriptions = [f"{self.get_id()}/request"]
        # self.default_subscriptions = []
        # # self.default_subscriptions.append(f"{self.get_id()}.+.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_REGISTRY}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_CONTROL}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_DISCOVERY}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_MANAGE}.request")
        # self.default_subscriptions.append(f"{self.get_id()}.{envdsEvent.TYPE_STATUS}.request")

        # #TODO: where to add this, wait for self.message_client
        # #      probably in fn to set default subs
        # if config and "part-of" in config:
        #     # part_of = config["part-of"].split(".")
        #     # parent = self.message_client.to_channel(part_of)
        #     # channels = "/".join([parent, "update"])
        #     channel = ".".join([config["part-of"], "+", "update"])
        #     self.default_subscriptions.append(channel)

        self.expired_reg_time = 60
        self.stale_reg_time = 10
        self.reg_monitor_time = 2

        self._registry = dict()
        self._registry_by_id = dict()

        # self.loop.create_task(self.run())
        self.loop.create_task(self.setup())
        self.do_run = True

    def set_config(self, config=None):
        self.use_namespace = False
        return super().set_config(config=config)

    def handle_config(self, config=None):
        super().handle_config(config=config)

        return

    async def setup(self):
        await super().setup()

        # while not self.status.ready(type=Status.TYPE_CREATE):
        #     self.logger.debug("waiting to create DAQSystemManager")
        #     await asyncio.sleep(1)
        # await self.create_manager()

        # add subscriptions for requests
        self.apply_subscription(".".join([self.get_id(), "+", "request"]))
        # add subscriptions for system/manager
        # if self.part_of:
        #     try:
        #         self.apply_subscription(
        #             ".".join(["envds.registry", "request"])
        #         )
        #         # self.apply_subscription(
        #         #     ".".join(["envds.system", self.part_of["name"], "+", "update"])
        #         # )
        #         # self.apply_subscription(
        #         #     ".".join(["envds.manager", self.part_of["name"], "+", "update"])
        #         # )
        #     except KeyError:
        #         pass

        self.loop.create_task(self.monitor_registry())
        self.loop.create_task(self.run())

    async def monitor_registry(self):
        """
        Loop to monitor status of registry
        """
        while True:
            for ns, namespace in self._registry.items():
                for kname, kind in namespace.items():
                    for name, reg in kind.items():
                        # dt = get_datetime()
                        # lu = reg["last-update"]
                        # ldt = string_to_datetime(reg["last-update"])
                        # self.logger.debug("%s", (dt-ldt).seconds)
                        diff = (get_datetime() - string_to_datetime(reg["last-update"])).seconds
                        if diff > self.expired_reg_time:
                            self.logger.debug("%s - %s - %s registration is expired")
                        elif  diff > self.stale_reg_time:
                            self.logger.debug("%s - %s - %s registration is stale", ns, kname, name)

            await asyncio.sleep(self.reg_monitor_time)

    async def handle_status(self, message, extra=dict()):

        if (action := Message.get_type_action(message)) :

            if action == envdsEvent.TYPE_ACTION_UPDATE:
                id = message["source"]
                self.refresh_registration_by_id(id)

    async def handle_registry(self, message, extra=dict()):

        if (action := Message.get_type_action(message)) :

            if action == envdsEvent.TYPE_ACTION_REQUEST:
                id = message["source"]
                data = message.data
                self.logger.debug("registry request: %s", message)

                try:
                    namespace = data[envdsEvent.TYPE_REGISTRY]["metadata"]["namespace"]
                    kind = data[envdsEvent.TYPE_REGISTRY]["kind"]
                    name = data[envdsEvent.TYPE_REGISTRY]["metadata"]["name"]

                    # create/update _registry
                    if namespace not in self._registry:
                        self._registry[namespace] = dict()
                    if kind not in self._registry[namespace]:
                        self._registry[namespace][kind] = dict()
                    self._registry[namespace][kind][name] = {
                        "id": id,
                        "created": get_datetime_string(),
                        "last-update": get_datetime_string(),
                    }

                    # create/update _registry_by_id
                    self._registry_by_id[id] = {
                        "namespace": namespace,
                        "kind": kind,
                        "name": name
                    }

                    data = {envdsEvent.TYPE_REGISTRY: "registered"}
                    response = self.create_registry_response(target=id, data=data)
                    await self.send_message(response)

                    # subscribe to status updates to refresh registry
                    self.apply_subscription(
                        ".".join([id, envdsEvent.TYPE_STATUS, "update"])
                    )

                except KeyError:
                    self.logger.info("could not register %s", id)
                    return

                # if "run" in data:
                #     try:
                #         control = data["run"]["type"]
                #         value = data["run"]["value"]
                #         if control == "shutdown" and value:
                #             await self.shutdown()
                #     except KeyError:
                #         self.logger("invalid run control message")
                #         pass

    def refresh_registration_by_id(self, id):
        if reg := self.get_registration_by_id(id):
            try:
                ns = reg["namespace"]
                kind = reg["kind"]
                name = reg["name"]
                self._registry[ns][kind][name]["last-update"] = get_datetime_string()
            except KeyError:
                pass

    def update_registration(self, id, namespace, kind, name):

        if not all([id, namespace, kind, name]):
            self.logger.debug("can't update registration")
            return

        # create/update _registry
        if namespace not in self._registry:
            self._registry[namespace] = dict()
        if kind not in self._registry[namespace]:
            self._registry[namespace][kind] = dict()
        self._registry[namespace][kind][name] = {
            "id": id,
            "created": get_datetime_string(),
            "last-update": get_datetime_string(),
        }

        # create/update _registry_by_id
        self._registry_by_id[id] = {
            "namespace": namespace,
            "kind": kind,
            "name": name
        }

    def get_registration_filter(self, namespace=None, kind=None, name=None):
        # allow user to get a list of registrations based on a filter
        pass


    def get_registration(self, namespace, kind, name):
        if not all([namespace, kind, name]):
            self.logger.debug("can't get registration")
            return None
        
        try:
            return self._registry[namespace][kind][name]
        except KeyError:
            return None

    def get_registration_by_id(self, id):
        if not id:
            self.logger.debug("can't get registration_by_id")
            return None

        try:
            reg = self._registry_by_id[id]
            return reg
            # return self.get_registration(meta["namespace"], meta["kind"], meta["name"])
        except KeyError:
            return None


    def create_registry_response(self, target=None, data=None, **kwargs):
        if not target:
            target = ".".join([self.app_sig, "registry"])
        type = envdsEvent.TYPE_REGISTRY
        action = envdsEvent.TYPE_ACTION_RESPONSE
        return self.create_message(
            type=type, action=action, data=data, target=target, **kwargs
        )

    # async def handle_control(self, message, extra=dict()):

    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_REQUEST:
    #             data = message.data
    #             if "run" in data:
    #                 try:
    #                     control = data["run"]["type"]
    #                     value = data["run"]["value"]
    #                     if control == "shutdown" and value:
    #                         await self.shutdown()
    #                 except KeyError:
    #                     self.logger("invalid run control message")
    #                     pass

    # async def shutdown(self):
    #     timeout = 10
    #     sec = 0
    #     # allow time for registered services to shutdown and unregister
    #     while len(self._registry) > 0 and sec <= timeout:
    #         sec += 1
    #         await asyncio.sleep(1)

    #     self.logger.info("shutdown")
    #     self.run_status = "SHUTDOWN"
    #     self.run = False
    #     return await super().shutdown()

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

        # apply subscriptions
        # self.apply_subscriptions(self.default_subscriptions)

        # self.run_status = "RUNNING"
        # self.logger.info("registry started")
        # self.do_run = True
        while self.do_run:
            await asyncio.sleep(1)


    async def shutdown(self):

        if (
            self.status.get_current_status(
                type=Status.TYPE_SHUTDOWN, state=Status.STATE_SHUTDOWN
            )
            != Status.SHUTTINGDOWN
        ):

            timeout = 0 # set back to 10
            sec = 0
            # allow time for registered services to shutdown and unregister
            while len(self._registry) > 0 and sec <= timeout:
                sec += 1
                await asyncio.sleep(1)

            # self.logger.info("shutdown")
            # self.run_status = "SHUTDOWN"
            # self.run = False

            # return await super().shutdown()

            # set status to creating
            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_SHUTDOWN,
                    state=Status.STATE_SHUTDOWN,
                    status=Status.SHUTTINGDOWN,
                    ready_status=Status.SHUTDOWN,
                )
            )

            # give a moment to let message propogate
            await asyncio.sleep(2)

            self.status.event(
                StatusEvent.create(
                    type=Status.TYPE_SHUTDOWN,
                    state=Status.STATE_SHUTDOWN,
                    status=Status.SHUTDOWN,
                )
            )

            while not self.status.ready(type=Status.TYPE_SHUTDOWN):
                self.logger.debug("waiting to finish shutdown")
                await asyncio.sleep(1)

            await super().shutdown()
            self.do_run = False



if __name__ == "main":
    pass
