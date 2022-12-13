import asyncio

from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    time_to_next,
)
from envds.envds.envds import envdsBase, envdsEvent
from envds.message.message import Message
from envds.status.status import Status, StatusEvent

class DAQInterfaceProxy(envdsBase):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)

        self.kind = "DAQInterfaceProxy"
        self.envds_id = ".".join([self.app_sig, "daqinterfaceproxy", self.namespace, self.name])

        self.interface = None

        self.loop.create_task(self.setup())
        self.do_run = True

    def handle_config(self, config=None):
        super().handle_config(config=config)

        # set self.name to mfg-model-serial
        # set defaults
        # set connections

        return

class DAQInterface(envdsBase):

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config, **kwargs)

        self.kind = "DAQInterface"
        self.envds_id = ".".join([self.app_sig, "daqinterface", self.namespace, self.name])

        self.run_settings = dict()
        self.attributes = dict()

        self.connections = dict()
        self.client = None

        self.loop.create_task(self.setup())
        self.do_run = True

    async def setup(self):
        await super().setup()


    def handle_config(self, config=None):
        super().handle_config(config=config)

        # set self.name to mfg-model-serial
        # set defaults
        # set connections

        return

    async def setup(self):
        await super().setup()
