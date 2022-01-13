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


# class DAQManager(envdsBase):
#     def __init__(self, config=None, **kwargs) -> None:
#         super().__init__(config=config, **kwargs)
#         pass


class DAQSystem(envdsBase):

    STATUS_STATE_MANAGER = "manager"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.name = "daq-system"
        self.kind = "DAQSystem"
        self.envds_id = ".".join([self.app_sig, "daq", self.namespace, self.name])

        self.manager = None

        self.loop.create_task(self.setup())
        self.do_run = True

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

    # async def create_manager(self, config=None):
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
    #     self.manager = True
    #     # self.manager = DAQSystemManager(config=self.config)
    #     if self.manager:

    #         # set status to created
    #         self.status.event(
    #             StatusEvent.create(
    #                 type=Status.TYPE_CREATE,
    #                 state=self.STATUS_STATE_MANAGER,
    #                 status=Status.CREATED,
    #             )
    #         )

    #     # start envdsManager
    #     # self.manager = DataSystemManager(config=self.config)
    #     pass

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

            # if get_datetime().second % 10 == 0:

            #     do_shutdown_req = True
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

            while not self.status.ready(type=Status.TYPE_SHUTDOWN):
                self.logger.debug("waiting to finish shutdown")
                await asyncio.sleep(1)

            await super().shutdown()
            self.do_run = False


class DAQController(envdsBase):

    STATUS_STATE_MANAGER = "manager"

    RUNSTATE_START = "start"
    RUNSTATE_STOP = "stop"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.name = "daq-system"
        self.kind = "DAQController"
        self.envds_id = ".".join([self.app_sig, "daqcontroller", self.namespace, self.name])

        self.manager = None

        self.loop.create_task(self.setup())
        self.do_run = True

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

    # async def create_manager(self, config=None):
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
    #     self.manager = True
    #     # self.manager = DAQSystemManager(config=self.config)
    #     if self.manager:

    #         # set status to created
    #         self.status.event(
    #             StatusEvent.create(
    #                 type=Status.TYPE_CREATE,
    #                 state=self.STATUS_STATE_MANAGER,
    #                 status=Status.CREATED,
    #             )
    #         )

    #     # start envdsManager
    #     # self.manager = DataSystemManager(config=self.config)
    #     pass

    # async def handle_runstate(self, message, extra=dict()):
    async def handle_runstate(self, message, extra=dict()):
        await super().handle_runstate(message, extra=extra)

        if (action := Message.get_type_action(message)) :

            if action == envdsEvent.TYPE_ACTION_REQUEST:
                data = message.data
                if envdsEvent.TYPE_RUNSTATE in data:
                    if data[envdsEvent.TYPE_RUNSTATE] == self.RUNSTATE_START:
                        await self.start()
                    elif data[envdsEvent.TYPE_RUNSTATE] == self.RUNSTATE_STOP:
                        await self.stop()

    async def handle_control(self, message, extra=dict()):
        pass
        # if (action := Message.get_type_action(message)) :

        #     if action == envdsEvent.TYPE_ACTION_REQUEST:
        #         data = message.data
        #         if "run" in data:
        #             try:
        #                 control = data["run"]["type"]
        #                 value = data["run"]["value"]
        #                 if control == "shutdown" and value:
        #                     await self.shutdown()
        #             except KeyError:
        #                 self.logger("invalid run control message")
        #                 pass

    async def enable(self):
        pass

    async def disable(self):
        pass

    async def start(self):
        pass

    async def stop(self):
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

            # if get_datetime().second % 10 == 0:

            #     do_shutdown_req = True
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

            while not self.status.ready(type=Status.TYPE_SHUTDOWN):
                self.logger.debug("waiting to finish shutdown")
                await asyncio.sleep(1)

            await super().shutdown()
            self.do_run = False


if __name__ == "__main__":
    pass


