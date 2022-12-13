from abc import abstractmethod, abstractstaticmethod
import asyncio
# import logging
# import signal
from envds.util.util import (
    get_datetime,
    get_datetime_string,
    datetime_mod_sec,
    time_to_next,
)

from envds.system.envds import envdsBase, envdsEvent
from envds.message.message import Message
from envds.status.status import Status, StatusEvent

class DAQInstrument(envdsBase):

    STATUS_STATE_MANAGER = "manager"

    RUNSTATE_START = "start"
    RUNSTATE_STOP = "stop"

    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        # self.name = "daq-system"
        self.kind = "DAQInstrument"
        self.envds_id = ".".join([self.app_sig, "daqinstrument", self.namespace, self.name])

        # self.manager = None

        self.serial_number = None # must be set at instantiation
        # instance values for attributes
        self.run_settings = {
            "controls": None, # map of control defaults?
            "connections": None # map of actual connection config
        }

        self.attributes = {
            "description": {
                "mfg": "mfg_id or short_name",
                "mfg_long": "full mfg name",
                "model": "model_name",
                "description": "", # "long description of instrument",
                "type": "", # "do I need this or will tags suffice?",            
                "tags": [], # list of tags
            },
            "parameters": None, # map of parameters available
            "controls": None, # map of controls
            "connections": None, # map of interface connections
        }

        self.loop.create_task(self.setup())
        self.do_run = True

    @abstractstaticmethod
    def get_attributes():
        pass

    def handle_config(self, config=None):
        super().handle_config(config=config)

        # set self.name to mfg-model-serial
        # set defaults
        # set connections

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

        # add interface proxy(ies) based on connections

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

            await self.shutdown_resources()

            # # simulate waiting for rest of resources to shut down 
            # for x in range(0,2):
            #     self.logger.debug("***simulating DAQSystem shutdown")
            #     await asyncio.sleep(1)
            
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



class DummyInstrument(DAQInstrument):
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

        self.mfg = "dmi"
        self.mfg_ = "dmi"
        self.model = "Alpha"

        self.serial_number = "1234"

        self.attributes = {
            "description": {
                "mfg": "dmi",
                "mfg_long": "Dummy Mfg Inc",
                "model": "alpha",
                "description": "Dummy Instrument for testing",
                "type": "", # "do I need this or will tags suffice?",            
                "tags": ["test", "dummy"], # list of tags
            },
            "parameters": {
                "primary": {
                    "1D": {

                    }
                }
            }
        }


    def get_attributes():
        
        attributes = dict()
        description = {
            "mfg": "dmi",
            "mfg_long": "Dummy Mfg Inc",
            "model": "alpha",
            "description": "Dummy Instrument for testing",
            "type": "", # "do I need this or will tags suffice?",            
            "tags": ["test", "dummy"], # list of tags
        }
        attributes["description"] = description

        connections = dict()
        '''
        "spec": {
            "class": {"module": "envds.daq.instrument", "class": "DummyInstrument"},
            "controls": {
                "sample_flow_sp": {
                    "default": 1.5
                }
            }
            "interface": {
                "data": {
                    "kind": "serial"
                    "protocol": "RS232",
                    "spec": {
                        "kind": "TCPInterface",
                        "metadata": {
                            "host": "10.55.169.53"
                            "port": "21"
                        }
                    }

                    "spec": {
                        "kind": "MoxaPort",
                        "metadata": {
                            "host": "xxx",
                            "port": "1"
                        }
                    }

                    "spec": {
                        "kind": "SerialInterface",
                        "metadata": {
                            "device": "/dev/ttyS0"
                        }
                    }

                    "options
                    "rs232": {
                        "interface-kind": "TCP",
                        "interface-uri": "10.55.169.51:21"
                    }
                },
                "enable": {
                    "DIO": {
                        "interface-kind": "GPIO",
                        "pin": 10
                    }
                },
                "enable": {
                    "kind": "analog",
                    "protocol": "DIO",
                    "spec": {
                        "kind": "GPIOInterface",
                        "metadata": {
                            "pin": "10"
                        }
                    }
                }
            }
            
        },
        '''
        interface = dict()
        interface["data"] = {
            "default": "serial",
            "serial": {
                "protocol": "RS232",
                "protocol_options": ["RS232", "RS422"],
                "settings": {
                    "baud": "9600",
                    "baud_options": ["9600", "19200"],
                    "parity": "N",
                    "stop_bits": 1,
                    "flow_control": "None",
                    "flow_control_options": ["None", "HW_control", "SW_control"]
                }
            },
            "analog": {
                "protocol": "AtoD",
            },
        
            # "rs232": {
            #     "baud": "9600",
            #     "baud_options": ["9600", "19200"],
            #     "parity": "N",
            #     "stop_bits": 1
            # },
            # "AtoD": {
            #     "volt_out_range": (0, 5), # ??
            # }
        }
        interface["enable"] = {
            "analog": {
                "protocol": "DIO",
                "protocol_options": ["DIO", "DtoA"]
            }
        }
        attributes["interface"] = interface
        # connections["enable"] = {
        #     "default": {
        #         "DIO": {}
        #     },
        #     "DIO": {
        #         "enable": "high",
        #         "disable": "low"
        #     }
        # }
        # attributes["connections"] = connections

        controls = dict()
        controls["sample_flow_sp"] = {
            "data_type": "NUMERIC",
            "units": "l min-1",
            "allowed_range": (0.5, 1.5),
            "default": 1.0,
            "label": "Sample Flow SP",
            "tags": ["flow"]
        }
        controls["sheath_flow_sp"] = {
            "data_type": "NUMERIC",
            "units": "l min-1",
            "allowed_range": (0.5, 3.5),
            "default": 2.5,
            "label": "Sheath Flow SP",
            "parse_label": None, # if needed
            "control_group": "Flows"
        }
        controls["heater_power"] = {
            "data_type": "NUMERIC",
            "units": "count",
            "allowed_range": (0, 1),
            "default": 0,
            "label": "Heater Power",
            "parse_label": None, # if needed
            "control_group": "Temperatures"
        }
        attributes["controls"] = controls


 

if __name__ == "__main__":
    pass

