import abc
import os
import sys
import uuid
from ulid import ULID
import asyncio
import logging
from logfmter import Logfmter
# from typing import Union
from pydantic import BaseModel
from cloudevents.http import CloudEvent
from envds.core import envdsBase, envdsAppID, envdsStatus
from envds.message.message import Message
from envds.daq.event import DAQEvent
from envds.daq.types import DAQEventType as det
from envds.exceptions import envdsRunTransitionException, envdsRunWaitException, envdsRunErrorException
from envds.daq.interface import Interface

from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)

from envds.daq.registration import init_sensor_registration, register_sensor #, get_sensor_registration, get_sensor_metadata

class SensorVariable(BaseModel):
    """docstring for SensorVariable."""
    name: str
    type: str | None = "str"
    shape: list[str] | None = ["time"]
    attributes: dict | None = dict()
    modes: list[str] | None = ["default"]

class SensorSetting(BaseModel):
    name: str
    type: str | None = "str"


# # class InstrumentInterface(BaseModel):
# #     """docstring for InstrumentInterface."""
# #     name: str
# #     interface_id: str
# #     port: str | None = None

# TODO: This could be BaseSettings?
class SensorConfig(BaseModel):
    """docstring for SensorConfig."""
    make: str
    model: str
    serial_number: str
    # variables: list | None = []
    variables: dict | None = {}
    interfaces: dict | None = {}
    daq: str | None = "default"

# class InstrumentMeta(BaseModel):
#     attributes: dict | None = dict()
#     variables: dict | None = {"time": {"shape": ["time"], "attributes": {"long_name": "Time"},}}

# class SensorStatus(envdsStatus):
#     """docstring for SensorStatus."""

#     SAMPLING = "sampling"

#     def __init__(self):
#         super(SensorStatus, self).__init__()

# class SensorInterface(object):
#     """docstring for SensorInterface."""
#     def __init__(self, config):
#         self.config = config
            
#         self.recv_buffer = asyncio.Queue()
#         self.send_buffer = asyncio.Queue()

#         self.configure(self)

#     def configure(self):
        
#         # TODO: this info should come from registry

#         self.interface_path = None
#         self.interface_id = None
#         if "interface_id" in self.config:
#             self.interface_id = self.config["interface_id"]

#         self.port = None
#         if "port" in self.config:
#             self.port = str(self.config["port"])

#         self.channel = None
#         if "channel" in self.config:
#             self.port = str(self.config["channel"])

#         if self.interface_id:
#             parts = []
#             parts.append("/envds")
#             parts.append("interface")
#             parts.append(self.interface_id)

#             if self.port or self.channel:
#                 if self.port:
#                     parts.append(self.port)
#                 else:
#                     parts.append(self.channel)
    
#                 self.interface_path = "/".join(parts)

#     async def send_data(self, data: CloudEvent, **extra):
#         if data:
#             await self.send_buffer.put(data)

#     async def send_message_loop(self):

#         while True:
#             # print("send_message_loop")
#             data = await self.send_buffer.get()
#             while not self.message_client:
#                 await asyncio.sleep(0.1)

#             iface_id = self.config["id"]
#             dest_path = f"{self.interface_path}/send"
#             message = Message(data=data, dest_path=dest_path)
#             await self.message_client.send(data)
#             await asyncio.sleep(.01)

#     async def rec_message_loop(self):

#         while True:
#             if self.message_client:
#                 data = await self.message_client.get()
#                 await self.recv_buffer.put(data)
#             await asyncio.sleep(0.01)




        
class Sensor(envdsBase):
    """docstring for Sensor."""

    # sensor states
    SAMPLING = "sampling"
    # CONNECTED = "connected"

    # ID_DELIM = "::"

    def __init__(self, config=None, **kwargs):
        super(Sensor, self).__init__(config=config, **kwargs)

        self.make = "DefaultMake"
        self.model = "DefaultModel"
        self.sn = str(ULID())
        
        self.iface_map = dict()

        # list of sampling tasks to start/stop in do_start
        self.sampling_task_list = []
        # running tasks
        self.sampling_tasks = []

        self.status.set_requested(Sensor.SAMPLING, envdsStatus.FALSE)
        # self.sensor_status_monitor_task = asyncio.create_task(self.sensor_status_monitor())


        self.run_state = "STOPPED"
        # self.metadata = InstrumentMeta()

        # set sensor id
        self.update_id("app_group", "sensor")
        self.update_id("app_ns", "envds")
        self.update_id("app_uid", f"make-model-{ULID()}")
        self.logger.debug("sensor id", extra={"self.id": self.id})

        self.status.set_id_AppID(self.id)
        self.status.set_state_param(Sensor.SAMPLING, requested=envdsStatus.FALSE, actual=envdsStatus.FALSE)


        # set default metadata interval
        self.include_metadata_interval = 60
        self.include_metadata = True
        self.run_task_list.append(self.send_metadata_loop())
        # asyncio.create_task(self.send_metadata_loop())

        self.run_task_list.append(self.interface_monitor())
        # self.instance_config["daq_id"] = "default"
        # if daq_id := os.getenv("DAQ_ID"):
        #     self.instance_config["daq_id"] = daq_id

    def configure(self):
        super(Sensor, self).configure()
        self.logger.debug("configure()")
        pass

    # can be overridden if metadata in another place
    def get_metadata(self):
        return self.metadata

    def run_setup(self):
        super().run_setup()

        self.logger = logging.getLogger(self.build_app_uid())
        self.update_id("app_uid", self.build_app_uid())

        init_sensor_registration()
        register_sensor(
            make=self.config.make,
            model=self.config.model,
            metadata=self.get_metadata()
        )

    def build_app_uid(self):
        parts = [
            self.config.make,
            self.config.model,
            self.config.serial_number
        ]
        return (Sensor.ID_DELIM).join(parts)

    def set_routes(self, enable: bool=True):
        super(Sensor, self).set_routes()
        pass

    #     topic_base = self.get_id_as_topic()
    #     self.set_route(
    #         subscription=f"{topic_base}/connect/update",
    #         route_key=det.interface_connect_update(),
    #         route=self.handle_interface_connect,
    #         enable=enable
    #     )

    def add_interface(self, name: str, interface: dict, update: bool = True):


        # dest_path = f"/envds/{iface_envds_env_id}/interface/{iface['interface_id']}/{iface['path']}/connect/request"
        # print(f"name:1 {name}, iface: {interface}")
        if name and interface:

            try:
                iface_env_id = interface["interface_env_id"]
            except KeyError:
                interface["interface_env_id"] = self.id.app_env_id

            # print(f"name:2 {name}, iface: {interface}")
            if name not in self.iface_map or update:
                self.iface_map[name] = {
                    "interface": interface,
                    "status": envdsStatus()
                }
                # print(f"name:3 {name}, iface: {interface}")
                self.iface_map[name]["status"].set_state_param(
                    envdsStatus.RUNNING,
                    requested=envdsStatus.TRUE,
                    actual=envdsStatus.TRUE,
                )
                # print(f"name:4 {name}, iface: {interface}")
                env_id = interface["interface_env_id"]
                id = interface["interface_id"]
                path = interface["path"]

                # print(f"name:5 {name}, iface: {interface}")
                self.set_route(
                    subscription=f"/envds/{env_id}/interface/{id}/{path}/status/update",
                    route_key=det.interface_status_update(),
                    route=self.handle_interface_status
                )
                # print(f"name:6 {name}, iface: {interface}")

 
        # if enable:
        #     self.message_client.subscribe(f"{topic_base}/connect/update")
        #     self.router.register_route(key=det.interface_connect_update(), route=self.handle_interface_connect)
        # else:
        #     self.message_client.unsubscribe(f"{topic_base}/connect/update")
        #     self.router.deregister_route(key=det.interface_connect_update(), route=self.handle_interface_connect)

        # self.message_client.subscribe(f"{topic_base}/status/request")
        # self.router.register_route(key=det.status_request(), route=self.handle_status)
        # # self.router.register_route(key=et.status_update, route=self.handle_status)

        # self.router.register_route(key=et.control_request(), route=self.handle_control)
        # # self.router.register_route(key=et.control_update, route=self.handle_control)

    async def handle_interface_data(self, message: Message):
        pass

    async def handle_interface_status(self, message: Message):
        if message.data["type"] == det.interface_status_update():
            self.logger.debug("handle_interface_status", extra={"type": det.interface_status_update()})

            # get path from message and update proper interface status

        pass

    async def status_check(self):

        # while True:

            # try:
        await super(Sensor,self).status_check()

        if not self.status.get_health(): # something has changed
            if not self.status.get_health_state(Sensor.SAMPLING):
                if self.status.get_requested(Sensor.SAMPLING) == envdsStatus.TRUE:
                    try:
                        await self.do_start()
                    except (envdsRunTransitionException, envdsRunErrorException, envdsRunWaitException):
                        pass
                    # self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRUE)
                else:
                    # self.disable()
                    # self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRANSITION)
                    try:
                        await self.do_stop()
                    except envdsRunTransitionException:
                        pass

        
        # await super(Sensor,self).status_check()

            # if not self.status.get_health_state(envdsStatus.RUNNING):
            #     if self.status.get_requested(envdsStatus.RUNNING) == envdsStatus.TRUE:
            #         self.do_run = True
            #     else:
            #         self.do_run = False
        # except Exception as e:
        #     self.logger.debug("sensor_status_monitor error", extra={"e": e})
        #     await asyncio.sleep(1)
        #     # print("here: 56")
        #     # await super(Sensor, self).status_monitor() # super has sleep
        #     # print("here: 57")

    # async def do_enable(self):

    #     try:
    #         await super(Sensor, self).do_enable()
    #     except envdsRunTransitionException:
    #         raise 
    #         # return

        # for name, iface in self.iface_map.items():
        #     dest_path = f"{self.get_id_as_topic()}/{id}/connect/request"
        #     extra_header = {"source_path": id}
        #     event = det.create_data_update(
        #         # source="envds.core", data={"test": "one", "test2": 2}
        #         source=self.get_id_as_source(),
        #         data=data,
        #         extra_header=extra_header
        #     )
        #     self.logger.debug("data update", extra={"event": event})
        #     message = Message(data=event, dest_path=dest_path)
        #     await self.send_message(message)


        # TODO: this should call enable_interface which will set the status request
        # # where to add interface? And should it be enabled/disabled, started/stopped?
        # for name, iface in self.config.interfaces.items():
        #     self.add_interface(name, iface)
        # # print("sensor.configure")

        # TODO: add this to enable task list
        # self.interface_task = asyncio.create_task(self.connect_interfaces())

        # TODO: set connect requested in interface status
        #  - this will trigger the connect loop to send a connection request

    # def interface_enable(self):
    #     # for name, iface in self.iface_map.items():
    #     #     iface.status.set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)

    #     for name, iface in self.iface_map.items():
    #         iface["status"].set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)

    # async def do_interface_enable(self):

    #      for name, iface in self.iface_map.items():
    #         requested = iface.status.get_requested(envdsStatus.ENABLED)
    #         actual = iface.status.get_actual(envdsStatus.ENABLED)

    #         if requested != envdsStatus.TRUE:
    #             raise envdsRunTransitionException(envdsStatus.ENABLED)

    #         if actual != envdsStatus.FALSE:
    #             raise envdsRunTransitionException(envdsStatus.ENABLED)
            
    #         iface.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRANSITION)

    def enable(self):
        # print("sensor.enable:1")
        super().enable()
        # print("sensor.enable:2")

        for name, iface in self.iface_map.items():
            # print("sensor.enable:3")
            iface["status"].set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)
            # print("sensor.enable:4")
        # print("sensor.enable:5")

    # def disable(self):
    #     if self.interface_task:
    #         self.interface_task.cancel()
    #     pass

    def disable(self):
        for name, iface in self.iface_map.items():
            iface["status"].set_requested(envdsStatus.ENABLED, envdsStatus.FALSE)

        super().disable()

    def sampling(self) -> bool:
        self.logger.debug("sensor.sampling")
        if self.status.get_requested(Sensor.SAMPLING) == envdsStatus.TRUE:
            return self.status.get_health_state(Sensor.SAMPLING)

    def start(self):

        if not self.enabled():
            self.enable()

        self.status.set_requested(Sensor.SAMPLING, envdsStatus.TRUE)

    async def do_start(self):
    
        try:
            # print("do_start:1")
            # self.enable()
            # print("do_start:2")
            # print("do_start:1")
            requested = self.status.get_requested(Sensor.SAMPLING)
            actual = self.status.get_actual(Sensor.SAMPLING)

            if requested != envdsStatus.TRUE:
                raise envdsRunTransitionException(Sensor.SAMPLING)

            if actual != envdsStatus.FALSE:
                raise envdsRunTransitionException(Sensor.SAMPLING)
            print("do_start:2")

            # self.enable()
            # print("do_start:3")

            # if not (
            #     self.status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE
            #     and self.status.get_health_state(envdsStatus.ENABLED)
            # ):
            #     return
            # while not self.status.get_health_state(envdsStatus.ENABLED):
            #     self.logger.debug("waiting for enable state to start sensor")
            #     await asyncio.sleep(1)

            if not self.enabled():
                raise envdsRunWaitException(Sensor.SAMPLING)
                # return

            # while not self.enabled():
            #     self.logger.info("waiting for sensor to become enabled")
            #     await asyncio.sleep(1)
            # print("do_start:4")

            self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRANSITION)
            # print("do_start:5")

            for task in self.sampling_task_list:
                # print("do_start:6")
                self.sampling_tasks.append(asyncio.create_task(task))
                # print("do_start:7")

            # # TODO: enable all interfaces
            # for name, iface in self.iface_map.items():
            #     iface["status"].set_requested(envdsStatus.ENABLED, envdsStatus.TRUE)

            # may need to require sensors to set this but would rather not
            self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRUE)
            # print("do_start:8")
            self.logger.debug("do_start complete", extra={"status": self.status.get_status()})

        except (envdsRunWaitException, TypeError) as e:
            self.logger.warn("do_start", extra={"error": e})
            # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.FALSE)
            # for task in self.enable_task_list:
            #     if task:
            #         task.cancel()
            raise envdsRunWaitException(Sensor.SAMPLING)

        except envdsRunTransitionException as e:
            self.logger.warn("do_start", extra={"error": e})
            # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.FALSE)
            # for task in self.enable_task_list:
            #     if task:
            #         task.cancel()
            raise envdsRunTransitionException(Sensor.SAMPLING)

        # except (envdsRunWaitException, envdsRunTransitionException) as e:
        #     self.logger.warn("do_enable", extra={"error": e})
        #     # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.FALSE)
        #     # for task in self.enable_task_list:
        #     #     if task:
        #     #         task.cancel()
        #     raise e(Sensor.SAMPLING)

        except (envdsRunErrorException, Exception) as e:
            self.logger.error("do_start", extra={"error": e})
            self.status.set_actual(Sensor.SAMPLING, envdsStatus.FALSE)
            for task in self.sampling_task_list:
                if task:
                    task.cancel()
            raise envdsRunErrorException(Sensor.SAMPLING)

        # self.run_state = "STARTING"
        # self.logger.debug("start", extra={"run_state": self.run_state})

    def stop(self):
        self.status.set_requested(Sensor.SAMPLING, envdsStatus.FALSE)

    async def do_stop(self):
        requested = self.status.get_requested(Sensor.SAMPLING)
        actual = self.status.get_actual(Sensor.SAMPLING)

        if requested != envdsStatus.FALSE:
            raise envdsRunTransitionException(Sensor.SAMPLING)

        if actual != envdsStatus.TRUE:
            raise envdsRunTransitionException(Sensor.SAMPLING)

        self.status.set_actual(Sensor.SAMPLING, envdsStatus.TRANSITION)

        for task in self.sampling_tasks:
            task.cancel()

        self.status.set_actual(Sensor.SAMPLING, envdsStatus.FALSE)

    def disable(self):
        self.stop()
        super().disable()

    # async def shutdown(self):
    #     # do sensor shutdown tasks
    #     self.stop()
    #     # do this after all is done
    #     await super(Sensor,self).shutdown()

    async def interface_monitor(self):

        while True:
            self.logger.debug("interface_monitor")
            try:
                await self.interface_check()
            except Exception as e:
                self.logger.debug("interface_status_monitor error", extra={"e": e})
            
            await asyncio.sleep(2)

    async def interface_check(self):
        # self.logger.debug("interface_check", extra={"iface_map": self.iface_map})
        for name, iface in self.iface_map.items():
            status = iface["status"]
            # self.logger.debug("interface_check", extra={"status": status.get_status()})
            if not status.get_health():
                if not status.get_health_state(envdsStatus.ENABLED):
                    if status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
                        try:
                            try:
                                iface_envds_id = iface["interface"]["interface_envds_env_id"]
                            except KeyError:
                                iface_envds_id = self.id.app_env_id

                            # dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface_id']}/{iface['path']}/connect/request"
                            dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/status/request"
                            extra_header = {"path_id": iface["interface"]["path"]}
                            # event = DAQEvent.create_interface_connect_request(
                            event = DAQEvent.create_interface_status_request(
                                # source="envds.core", data={"test": "one", "test2": 2}
                                source=self.get_id_as_source(),
                                # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                                data={"state": envdsStatus.ENABLED, "requested": envdsStatus.TRUE},
                                extra_header=extra_header
                            )
                            self.logger.debug("enable interface", extra={"n": name, "e": event, "dest_path": dest_path})
                            message = Message(data=event, dest_path=dest_path)
                            # self.logger.debug("interface check", extra={"dest_path": dest_path})
                            await self.send_message(message)

                            # set the route to recv data
                            self.set_route(
                                subscription=f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/data/update",
                                route_key=det.interface_data_recv(),
                                # route=iface["recv_task"]
                                route=self.handle_interface_data
                            )
                        except Exception as e:
                            self.logger.error("interface_check", extra={"error": e})
                    else:

                        try:
                            iface_envds_id = iface["interface"]["interface_envds_env_id"]
                        except KeyError:
                            iface_envds_id = self.id.app_env_id

                        # dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface_id']}/{iface['path']}/connect/request"
                        dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/status/request"
                        extra_header = {"path_id": iface['interface']["path"]}
                        # event = DAQEvent.create_interface_connect_request(
                        event = DAQEvent.create_interface_status_request(
                            # source="envds.core", data={"test": "one", "test2": 2}
                            source=self.get_id_as_source(),
                            # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                            data={"state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                            extra_header=extra_header
                        )
                        self.logger.debug("connect interface", extra={"n": name, "e": event})
                        message = Message(data=event, dest_path=dest_path)
                        await self.send_message(message)

                        # remove route
                        self.set_route(
                            subscription=f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/data/update",
                            route_key=det.interface_data_recv(),
                            # route=iface["recv_task"],
                            route=self.handle_interface_data,
                            enable=False
                        )


            else:
                if status.get_health_state(envdsStatus.ENABLED):
                    try:
                        iface_envds_id = iface["interface"]["interface_envds_env_id"]
                    except KeyError:
                        iface_envds_id = self.id.app_env_id

                    dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/keepalive/request"
                    extra_header = {"path_id": iface["interface"]["path"]}
                    event = DAQEvent.create_interface_keepalive_request(
                        # source="envds.core", data={"test": "one", "test2": 2}
                        source=self.get_id_as_source(),
                        # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                        data={},
                        extra_header=extra_header
                    )
                    # # event = DAQEvent.create_interface_connect_request(
                    # event = DAQEvent.create_interface_keepalive_request(
                    #     # source="envds.core", data={"test": "one", "test2": 2}
                    #     source=self.get_id_as_source(),
                    #     data={"path_id": iface["path"]} #, "state": envdsStatus.ENABLED, "requested": envdsStatus.TRUE},
                    # )
                    self.logger.debug("interface keepalive request", extra={"n": name, "e": event})
                    message = Message(data=event, dest_path=dest_path)
                    await self.send_message(message)
    

    # async def connect_interface(self, name):

    #     if name:
    #         try:
    #             interface = self.iface_map[name]

    #         except KeyError:
    #             pass

    # async def connect_interfaces(self):
    #     for name, iface in self.iface_map.items():
    #         self.logger.debug("connect_interfaces", extra={"name": name, "iface": iface})
        
    #     # send message to interface:
    #     #   - request connect (also acts to register)
    #     #   - start keepalive loop
    #     #       - keepalive loop sends simple ping to maintain registry
    #     #   - register interface/status/updates route
    #     #   - start interface monitor
    #     #       - check for dis/connects

    async def update_registry(self):
        await super().update_registry()

        # update sensor definition on db/redis
        # update sensor instance on db/redis
        # send registry_update message

    async def send_metadata_loop(self):

        while True:
            if self.include_metadata_interval > 0:
                # wt = utilities.util.time_to_next(
                #     self.include_metadata_interval
                # )
                # print(f'wait time: {wt}')
                await asyncio.sleep(time_to_next(self.include_metadata_interval))
                self.include_metadata = True
            else:
                self.include_metadata = True
                await asyncio.sleep(1)

    def build_data_record(self, meta: bool = False, mode: str = "default") -> dict:
        record = {
            "attributes": {
                "make": self.config.make,
                "model": self.config.model,
                "serial_number": self.config.serial_number,
                "sampling_mode": mode,
                "data_format": "envds-1.0",
            },
            "variables": {},
        }

        # print(record)
        for name, var in self.config.variables.items():
            # print(f"name: {name}, var: {var}")
            record["variables"][name] = {"data": None}
            if meta:
                record["variables"][name]["type"] = var.type
                record["variables"][name]["shape"] = var.shape
                record["variables"][name]["attributes"] = var.attributes
        return record
    
    # async def send_interface_data(self, data: CloudEvent, interface: SensorInterface):
    #     # build Message using iface meta
    #     message = None

    #     await self.message_client.send_message(message)


    