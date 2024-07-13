import abc
import os
import sys
import uuid
from ulid import ULID
import asyncio
import logging
from logfmter import Logfmter
# from typing import Union
from pydantic import BaseModel, ValidationError, validator
from typing import Any
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

from envds.daq.db import init_db_models, register_sensor_type

# from envds.daq.registration import init_sensor_registration, register_sensor #, get_sensor_registration, get_sensor_metadata

# class SensorVariable(BaseModel):
#     """docstring for SensorVariable."""
#     name: str
#     type: str | None = "str"
#     shape: list[str] | None = ["time"]
#     attributes: dict | None = dict()
#     modes: list[str] | None = ["default"]

# class SensorAttribute(BaseModel):
#     name: str
#     type: str | None = "str"
#     value: Any
    
#     @validator("value")
#     def value_check(cls, v, values):
#         if "type" in values and not isinstance(v, eval(values["type"])):
#             raise ValueError('attribute value is wrong type')
#         return v


# class SensorSetting(BaseModel):
#     name: str
#     type: str | None = "str"


# # # class InstrumentInterface(BaseModel):
# # #     """docstring for InstrumentInterface."""
# # #     name: str
# # #     interface_id: str
# # #     port: str | None = None

# # TODO: This could be BaseSettings?
# class SensorConfig(BaseModel):
#     """docstring for SensorConfig."""
#     make: str
#     model: str
#     serial_number: str
#     # variables: list | None = []
#     variables: dict | None = {}
#     interfaces: dict | None = {}
#     daq: str | None = "default"


class SensorAttribute(BaseModel):
    # name: str
    type: str | None = "str"
    data: Any

    @validator("data")
    def data_check(cls, v, values):
        if "type" in values:
            data_type = values["type"]
            if data_type == "char" or data_type == "string":
                data_type = "str"
                
            if "type" in values and not isinstance(v, eval(data_type)):
                raise ValueError("attribute data is wrong type")
        return v

class SensorVariable(BaseModel):
    """docstring for SensorVariable."""

    # name: str
    type: str | None = "str"
    shape: list[str] | None = ["time"]
    attributes: dict[str, SensorAttribute]
    # attributes: dict | None = dict()
    # modes: list[str] | None = ["default"]

class SensorSetting(BaseModel):
    """docstring for SensorSetting."""

    # name: str
    type: str | None = "str"
    shape: list[str] | None = ["time"]
    attributes: dict[str, SensorAttribute]
    # attributes: dict | None = dict()
    # modes: list[str] | None = ["default"]

class SensorMetadata(BaseModel):
    """docstring for SensorMetadata."""
    attributes: dict[str, SensorAttribute]
    variables: dict[str, SensorVariable]
    settings: dict[str, SensorSetting]

class SensorConfig(BaseModel):
    """docstring for SensorConfig."""

    make: str
    model: str
    serial_number: str
    metadata: SensorMetadata
    # # variables: list | None = []
    # attributes: dict[str, SensorAttribute]
    # variables: dict[str, SensorVariable]
    # # # variables: dict | None = {}
    # settings: dict[str, SensorSetting]
    interfaces: dict | None = {}
    daq: str | None = "default"

class RuntimeSettings(object):
    """docstring for RuntimeSettings."""
    def __init__(self, settings: dict = None):

        if settings is None:
            self.settings = dict()
    
    def set_setting(self, name: str, requested, actual=None):
        if name not in self.settings:
            self.settings[name] = dict()

        self.settings[name]["requested"] = requested
        self.settings[name]["actual"] = actual

    def get_setting(self, name: str):
        if name in self.settings:
            return self.settings[name]
        return None
    
    def get_settings(self):
        return self.settings
    
    def get_health_setting(self, name: str) -> bool:
        if (setting:=self.get_setting(name)) is not None:
            return setting["requested"] == setting["actual"]
        return False
    
    def get_health(self) -> bool:
        for name in self.settings.keys():
            if not self.get_health_setting(name):
                return False
        return True    


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
        
        # default format version, inherited can override
        self.sensor_format_version = "1.0.0"

        self.iface_map = dict()

        self.settings = RuntimeSettings()

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

        self.sampling_interval = 1 # default collection interval in seconds
        
        # set default metadata interval
        self.include_metadata_interval = 60
        self.include_metadata = True
        self.run_task_list.append(self.send_metadata_loop())
        # asyncio.create_task(self.send_metadata_loop())

        self.enable_task_list.append(self.interface_config_monitor())
        self.run_task_list.append(self.interface_monitor())
        self.run_task_list.append(self.settings_monitor())
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

        asyncio.create_task(self.register_sensor_type())

        # TODO: decide if sensor self registers or send registry request (I think latter)
        # init_sensor_registration()
        # register_sensor(
        #     make=self.config.make,
        #     model=self.config.model,
        #     metadata=self.get_metadata()
        # )

    async def register_sensor_type(self):
        # await init_db_models()
        while True:
            await register_sensor_type(
                make=self.get_make(), model=self.get_model(), metadata=self.get_metadata()
            )
            await asyncio.sleep(10)

    def get_make(self):
        return self.config.make
    
    def get_model(self):
        return self.config.model

    def get_serial_number(self):
        return self.config.serial_number

    def build_app_uid(self):
        parts = [
            self.get_make(),
            self.get_model(),
            self.get_serial_number()
        ]
        return (self.ID_DELIM).join(parts)

    def set_routes(self, enable: bool=True):
        super(Sensor, self).set_routes()

        topic_base = self.get_id_as_topic()
        self.set_route(
            subscription=f"{topic_base}/settings/request",
            route_key=det.sensor_settings_request(),
            route=self.handle_settings,
            enable=enable
        )

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

    async def handle_settings(self, message: Message):
        if message.data["type"] == det.sensor_settings_request():
            try:
                src = message.data["source"]
                setting = message.data.data.get("settings", None)
                requested = message.data.data.get("requested", None)
                self.logger.debug("handle_settings", extra={"source": src, "setting": setting})
                if setting and requested:
                    # name = setting["settings"]
                    current = self.settings.get_setting(setting)
                    self.settings.set_setting(
                        name=setting,
                        requested=requested,
                        actual=current["actual"]
                    )

            except (KeyError,Exception) as e:
                self.logger.error("databuffer save error", extra={"error": e})


    async def handle_interface_data(self, message: Message):
        pass

    async def handle_status(self, message: Message):
        await super().handle_status(message)
        # self.logger.debug("handle_status", extra={"data": message.data, "path": message.dest_path})
        if message.data["type"] == det.status_request():
            try:
                # self.logger.debug("handle_status", extra={"data.data": message.data.data})
                state = message.data.data.get("state", None)
                # self.logger.debug("handle_status", extra={"type": det.status_request(), "state": state})
                if state and state == self.SAMPLING:
                    requested = message.data.data.get("requested", None)
                    # self.logger.debug("handle_status", extra={"type": det.status_request(), "state": state, "requested": requested})
                    if requested:
                        # self.logger.debug("handle_status", extra={"type": det.status_request(), "state": state, "requested": requested})
                        if requested == envdsStatus.TRUE:
                            self.start()
                        elif requested == envdsStatus.FALSE:
                            self.stop()
                    await self.send_status_update()
            except Exception as e:
                self.logger.error("handle_status", extra={"error": e})

        
            # get path from message and update proper interface status

        pass

    async def handle_interface_status(self, message: Message):
        if message.data["type"] == det.interface_status_update():
            # self.logger.debug("handle_interface_status", extra={"type": det.interface_status_update(), "data":message.data})

            # get path from message and update proper interface status
            try:
                client_id = message.data["path_id"]
                for name, interface in self.iface_map.items():
                    # self.logger.debug("handle_interface_status", extra={"iface": interface})
                    if interface["interface"]["path"] == client_id:
                        # self.logger.debug("handle_interface_status", extra={"status": interface["status"].get_status()})
                        # self.logger.debug("handle_interface_status", extra={"data": message.data.data["state"]})
                        
                        interface["status"].set_state(message.data.data["state"])

            except Exception as e:
                self.logger.error("handle_interface_status", extra={"error": e})
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

    async def settings_monitor(self):

        send_settings = True
        while True:
            try:
                await self.settings_check()
            except Exception as e:
                self.logger.error("settings_monitor", extra={"error": e})
            
            if self.enabled() and send_settings:
                # send settings every other second
                event = DAQEvent.create_sensor_settings_update(
                    # source="sensor.mockco-mock1-1234", data=record
                    source=self.get_id_as_source(),
                    data={"settings": self.settings.get_settings()},
                )
                dest_path = f"/{self.get_id_as_topic()}/settings/update"
                self.logger.debug(
                    "settings_monitor", extra={"data": event, "dest_path": dest_path}
                )
                message = Message(data=event, dest_path=dest_path)
                # self.logger.debug("default_data_loop", extra={"m": message})
                await self.send_message(message)

            send_settings = not send_settings
            await asyncio.sleep(1)

    # each sensor should handle this as required
    async def settings_check(self):
        pass

    async def interface_send_data(self, data: dict, path_id: str = "default"):

        try:
            iface = self.iface_map[path_id]
        except KeyError:
            return
        
        try:
            try:
                iface_envds_id = iface["interface"]["interface_envds_env_id"]
            except KeyError:
                iface_envds_id = self.id.app_env_id

            dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/data/send"
            extra_header = {"path_id": iface["interface"]["path"]}
            # event = DAQEvent.create_interface_connect_request(
            event = DAQEvent.create_interface_data_send(
                # source="envds.core", data={"test": "one", "test2": 2}
                source=self.get_id_as_source(),
                # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                data={"data": data},
                extra_header=extra_header
            )
            self.logger.debug("interface_send_data", extra={"n": path_id, "e": event, "dest_path": dest_path})
            message = Message(data=event, dest_path=dest_path)
            self.logger.debug("interface_send_data", extra={"dest_path": dest_path})
            await self.send_message(message)
        except Exception as e:
            self.logger.error("interface_send_data", extra={"error": e})

    async def interface_config_monitor(self):
        # if client enabled, send connection, read/write properties to client(s) one time
        send_config = True
        while True:

            # self.logger.debug("client_config_monitor", extra={"send_config": send_config})
            while not self.enabled():
                print("here:2")
                send_config = True
                await asyncio.sleep(1)
            if send_config:

                for name, iface in self.iface_map.items():
                    # status = iface["status"]
                    # self.logger.debug("interface_check", extra={"status": status.get_status()})
                    # if not status.get_health():
                    #     if not status.get_health_state(envdsStatus.ENABLED):
                    #         if status.get_requested(envdsStatus.ENABLED) == envdsStatus.TRUE:
                    try:
                        try:
                            iface_envds_id = iface["interface"]["interface_envds_env_id"]
                        except KeyError:
                            iface_envds_id = self.id.app_env_id

                        try:
                            print(f"iface: {iface}")
                            config_data = {"path": iface["interface"]["path"], "sensor-interface-properties": iface["interface"]["sensor-interface-properties"]}
                        except KeyError:
                            break

                        self.logger.debug("client_config_monitor", extra={"id": name, "data": config_data})
                        # dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface_id']}/{iface['path']}/connect/request"
                        dest_path = f"/envds/{iface_envds_id}/interface/{iface['interface']['interface_id']}/{iface['interface']['path']}/config/request"
                        extra_header = {"path_id": iface["interface"]["path"]}
                        # event = DAQEvent.create_interface_connect_request(
                        event = DAQEvent.create_interface_config_request(
                            # source="envds.core", data={"test": "one", "test2": 2}
                            source=self.get_id_as_source(),
                            # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
                            data={"config": config_data},
                            extra_header=extra_header
                        )
                        self.logger.debug("client_config_monitor", extra={"n": name, "e": event, "dest_path": dest_path})
                        message = Message(data=event, dest_path=dest_path)
                        self.logger.debug("client_config_monitor", extra={"dest_path": dest_path})
                        await self.send_message(message)
                        send_config = False
                    except Exception as e:
                        self.logger.error("client_config_monitor", extra={"error": e})
            await asyncio.sleep(1)

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
        # self.logger.debug("sensor.sampling")
        if self.status.get_requested(Sensor.SAMPLING) == envdsStatus.TRUE:
            # self.logger.debug("sampling", extra={"health": self.status.get_health_state(Sensor.SAMPLING)})
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
        self.logger.debug("do_stop")
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
            try:
                status = iface["status"]
                self.logger.debug("interface_check", extra={"status": status.get_status()})
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
            except Exception as e:
                self.logger.error("interface_check error", extra={"error": e})

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

        dest_path = f"/envds/{self.id.app_env_id}/sensor/registry/update"
        event = DAQEvent.create_sensor_registry_update(
            # source="envds.core", data={"test": "one", "test2": 2}
            source=self.get_id_as_source(),
            # data={"path_id": iface["path"], "state": envdsStatus.ENABLED, "requested": envdsStatus.FALSE},
            data={
                "make": self.get_make(),
                "model": self.get_model(),
                "serial_number": self.get_serial_number(),
            },
            # extra_header=extra_header
        )
        # # event = DAQEvent.create_interface_connect_request(
        # event = DAQEvent.create_interface_keepalive_request(
        #     # source="envds.core", data={"test": "one", "test2": 2}
        #     source=self.get_id_as_source(),
        #     data={"path_id": iface["path"]} #, "state": envdsStatus.ENABLED, "requested": envdsStatus.TRUE},
        # )
        self.logger.debug("sensor registry update", extra={"e": event})
        message = Message(data=event, dest_path=dest_path)
        await self.send_message(message)


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
        #TODO: change data_format -> format_version

        record = {
            # "time": get_datetime_string(),
            "timestamp": get_datetime_string(),
            # "instance": {
            #     "serial_number": self.config.serial_number,
            #     "sampling_mode": mode,
            # }
        }
        # print(record)
        if meta:
            record["attributes"] = self.config.metadata.dict()["attributes"]
            # print(record)
            record["attributes"]["serial_number"] = {
                "type": "char",
                }
            record["attributes"]["mode"] = {
                "type": "char",
                }
        else:
            record["attributes"] = {
                "make": {"data": self.config.make},
                "model": {"data": self.config.model},
                # "serial_number": self.config.serial_number,
                # "sampling_mode": mode,
                "format_version": {"data": self.sensor_format_version},
            }
        record["attributes"]["serial_number"] = {"data": self.config.serial_number}
        record["attributes"]["mode"] = {"data": mode}

        # print(record)
        
        #     "variables": {},
        # }

        # record["variables"] = dict()
        if meta:
            record["variables"] = self.config.metadata.dict()["variables"]
            # print(record)
            for name,_ in record["variables"].items():
                if "variable_type" in record["variables"][name]["attributes"] and record["variables"][name]["attributes"]["data"] == "setting":
                    record["variables"][name]["data"] = self.settings[name]["actual"]
                else:
                    record["variables"][name]["data"] = None
            # print(record)
        else:
            record["variables"] = dict()
            for name,_ in self.config.metadata.variables.items():
                if "variable_type" in record["variables"][name]["attributes"] and record["variables"][name]["attributes"]["data"] == "setting":
                    record["variables"][name] = {"data": self.settings[name]["actual"]}
                else:
                    record["variables"][name] = {"data": None}
        # # print(record)
        # for name, var in self.config.variables.items():
        #     # print(f"name: {name}, var: {var}")
        #     record["variables"][name] = {"data": None}
        #     if meta:
        #         record["variables"][name]["type"] = var.type
        #         record["variables"][name]["shape"] = var.shape
        #         record["variables"][name]["attributes"] = var.attributes
        return record
    
    def build_settings_record(self, meta: bool = False, mode: str = "default") -> dict:
        #TODO: change data_format -> format_version

        record = {
            # "time": get_datetime_string(),
            "timestamp": get_datetime_string(),
            # "instance": {
            #     "serial_number": self.config.serial_number,
            #     "sampling_mode": mode,
            # }
        }
        # print(record)
        if meta:
            record["attributes"] = self.config.metadata.dict()["attributes"]
            # print(record)
            record["attributes"]["serial_number"] = {
                "type": "char",
                }
            record["attributes"]["mode"] = {
                "type": "char",
                }
        else:
            record["attributes"] = {
                "make": {"data": self.config.make},
                "model": {"data": self.config.model},
                # "serial_number": self.config.serial_number,
                # "sampling_mode": mode,
                "format_version": {"data": self.sensor_format_version},
            }
        record["attributes"]["serial_number"] = {"data": self.config.serial_number}
        record["attributes"]["mode"] = {"data": mode}

        # print(record)
        
        #     "variables": {},
        # }

        # record["variables"] = dict()
        if meta:
            record["settings"] = self.config.metadata.dict()["settings"]
            # print(record)
            for name,_ in record["settings"].items():
                record["settings"][name]["data"] = None
            # print(record)
        else:
            record["settings"] = dict()
            for name,_ in self.config.metadata.variables.items():
                record["settings"][name] = {"data": None}
        return record


    