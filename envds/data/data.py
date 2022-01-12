import asyncio
# import sys
from envds.envds.envds import envdsBase, envdsEvent
from envds.message.message import Message
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    string_to_datetime,
    time_to_next,
)
from envds.status.status import Status, StatusEvent


class envdsDataManager(envdsBase):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.use_namespace = False
        self.kind = "DataManager"
        # self.envds_id = ".".join([self.envds_id, "registry"])
        self.envds_id = ".".join([self.app_sig, "datamanager"])

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

        # self.expired_reg_time = 60
        # self.stale_reg_time = 10
        # self.reg_monitor_time = 2

        # self._registry = dict()
        # self._registry_by_source = dict()

        # self._registry = {
        #     "services": None
        # }

        # self.logger.info("registry started")
        # extra = {"channel": "envds/registry/status"}
        # status = Message.create(
        #     source=self.envds_id,
        #     type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
        #     data={"update": "registry started"},
        #     **extra,
        # )
        # self.loop.create_task(self.send_message(status))
        # self.loop.create_task(self.run())
        self.loop.create_task(self.setup())
        self.do_run = True


    # async def handle_registry(self, message, extra=dict()):

    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_REQUEST:
    #             data = message.data
    #             if data["request"] == "register":

    #                 # begin shutting down system
    #                 # self.logger.info("shutdown requested")
    #                 # extra = {"channel": "evnds/system/request"}
    #                 # request = Message.create(
    #                 #     source=self.envds_id,
    #                 #     type=envdsEvent.TYPE_ACTION_REQUEST,
    #                 #     data=data,
    #                 #     **extra,
    #                 # )
    #                 await self.shutdown()

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
        self.apply_subscription(".".join(["envds", "data", "update"]))
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

        # self.loop.create_task(self.monitor_registry())
        self.loop.create_task(self.run())

    # async def monitor_registry(self):
    #     """
    #     Loop to monitor status of registry
    #     """
    #     while True:
    #         for ns, namespace in self._registry.items():
    #             for kname, kind in namespace.items():
    #                 for name, reg in kind.items():
    #                     # dt = get_datetime()
    #                     # lu = reg["last-update"]
    #                     # ldt = string_to_datetime(reg["last-update"])
    #                     # self.logger.debug("%s", (dt-ldt).seconds)
    #                     diff = (get_datetime() - string_to_datetime(reg["last-update"])).seconds
    #                     if diff > self.expired_reg_time:
    #                         self.logger.debug("%s - %s - %s registration is expired")
    #                     elif  diff > self.stale_reg_time:
    #                         self.logger.debug("%s - %s - %s registration is stale", ns, kname, name)

    #         await asyncio.sleep(self.reg_monitor_time)

    async def handle_data(self, message, extra=dict()):

        if (action := Message.get_type_action(message)) :

            if action == envdsEvent.TYPE_ACTION_UPDATE:
                source = message["source"]
                self.logger.debug("handle data: %s", source)

    # async def handle_status(self, message, extra=dict()):

    #     if (action := Message.get_type_action(message)) :

    #         if action == envdsEvent.TYPE_ACTION_UPDATE:
    #             source = message["source"]
    #             self.refresh_registration_by_source(source)


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

            # flush all data

            # set status to shuttingdown
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
