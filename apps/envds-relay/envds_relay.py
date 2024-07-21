import asyncio
import ulid
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import sys
import os
import json
import logging
from logfmter import Logfmter
import logging.config
from pydantic import BaseSettings, Field
from envds.core import envdsBase, envdsLogger
from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)

# from envds.message.message import Message
from envds.message.message import Message
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured
from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as bet

# from envds.daq.sensor import Sensor

# from typing import Union

from pydantic import BaseModel
import yaml
from aiomqtt import Client, MqttError

task_list = []


# class DataFile:
#     def __init__(
#         self,
#         base_path="/data",
#         save_interval=60,
#         file_interval="day",
#         # config=None,
#     ):

#         self.logger = logging.getLogger(self.__class__.__name__)

#         self.base_path = base_path

#         # unless specified, flush file every 60 sec
#         self.save_interval = save_interval

#         # allow for cases where we want hour files
#         #   options: 'day', 'hour'
#         self.file_interval = file_interval

#         # if config:
#         #     self.setup(config)

#         # if self.base_path[-1] != '/':
#         #     self.base_path += '/'

#         self.save_now = True
#         # if save_interval == 0:
#         #     self.save_now = True

#         self.current_file_name = ""

#         self.data_buffer = asyncio.Queue()

#         self.task_list = []
#         self.loop = asyncio.get_event_loop()

#         self.file = None

#         self.open()

#     async def write_message(self, message: Message):
#         # print(f"write_message: {message}")
#         # print(f"write_message: {message.data}")
#         # print(f'{msg.to_json()}')
#         await self.write(message.data)
#         # if 'body' in msg and 'DATA' in msg['body']:
#         #     await self.write(msg['body']['DATA'])

#     async def write(self, data_event: CloudEvent):
#         # add message to queue and return
#         # print(f'write: {data}')
#         # print(f"write: {data_event}")
#         await self.data_buffer.put(data_event.data)
#         qsize = self.data_buffer.qsize()
#         if qsize > 5:
#             self.logger.warn("write buffer filling up", extra={"qsize": qsize})

#     async def __write(self):

#         while True:

#             data = await self.data_buffer.get()
#             # print(f'datafile.__write: {data}')

#             try:
#                 dts = data["variables"]["time"]["data"]
#                 d_and_t = dts.split("T")
#                 ymd = d_and_t[0]
#                 hour = d_and_t[1].split(":")[0]
#                 # print(f"__write: {dts}, {ymd}, {hour}")
#                 self.__open(ymd, hour=hour)
#                 if not self.file:
#                     return

#                 json.dump(data, self.file)
#                 self.file.write("\n")

#                 if self.save_now:
#                     self.file.flush()
#                     if self.save_interval > 0:
#                         self.save_now = False

#             except KeyError:
#                 pass

#             # if data and ('DATA' in data):
#             #     d_and_t = data['DATA']['DATETIME'].split('T')
#             #     ymd = d_and_t[0]
#             #     hour = d_and_t[1].split(':')[0]

#             #     self.__open(ymd, hour=hour)

#             #     if not self.file:
#             #         return

#             #     json.dump(data, self.file)
#             #     self.file.write('\n')

#             #     if self.save_now:
#             #         self.file.flush()
#             #         if self.save_interval > 0:
#             #             self.save_now = False

#     def __open(self, ymd, hour=None):

#         fname = ymd
#         if self.file_interval == "hour":
#             fname += "_" + hour
#         fname += ".jsonl"

#         # print(f"__open: {self.file}")
#         if (
#             self.file is not None
#             and not self.file.closed
#             and os.path.basename(self.file.name) == fname
#         ):
#             return

#         # TODO: change to raise error so __write can catch it
#         try:
#             # print(f"base_path: {self.base_path}")
#             if not os.path.exists(self.base_path):
#                 os.makedirs(self.base_path, exist_ok=True)
#         except OSError as e:
#             self.logger.error("OSError", extra={"error": e})
#             # print(f'OSError: {e}')
#             self.file = None
#             return
#         # print(f"self.file: before")
#         self.file = open(
#             # self.base_path+fname,
#             os.path.join(self.base_path, fname),
#             mode="a",
#         )
#         self.logger.debug(
#             "_open",
#             extra={"file": self.file, "base_path": self.base_path, "fname": fname},
#         )
#         # print(f"open: {self.file}, {self.base_path}, {fname}")

#     def open(self):
#         self.logger.debug("DataFile.open")
#         self.task_list.append(asyncio.create_task(self.save_file_loop()))
#         self.task_list.append(asyncio.create_task(self.__write()))

#     def close(self):

#         for t in self.task_list:
#             t.cancel()

#         if self.file:
#             try:
#                 self.file.flush()
#                 self.file.close()
#                 self.file = None
#             except ValueError:
#                 self.logger.info("file already closed")
#                 # print("file already closed")

#     async def save_file_loop(self):

#         while True:
#             if self.save_interval > 0:
#                 await asyncio.sleep(time_to_next(self.save_interval))
#                 self.save_now = True
#             else:
#                 self.save_now = True
#                 await asyncio.sleep(1)

class MQTTRelayClient():
    """docstring for MQTTClient."""
    def __init__(self, config):
        super(MQTTRelayClient, self).__init__()
        self.logger = logging.getLogger(__name__)
    
        self.client_id = str(ulid.ULID())
        self.client = None

        self.config = config
        self.pub_data = self.config.get("pub-data-buffer", None)
        self.sub_data = self.config.get("sub-data-buffer", None)

        self.subscriptions = []

        self.run_task_list = []
        self.run_task_list.append(asyncio.create_task(self.relay_publisher()))
        self.run_task_list.append(asyncio.create_task(self.run()))
        self.do_run = True

    async def relay_publisher(self):
        reconnect_interval = 5
        while self.do_run:
            print(f"relay_publisher: {self.do_run}, {self.connected}")
            if self.connected:
                msg = await self.pub_data.get()
                self.logger.debug("relay_publisher", extra={"paylaod": msg})
                await asyncio.sleep(.1)
    # async def sender(sensor_config, start_time, end_time):

    #     parts = sensor_config["sensor-id"].split("::")
    #     mfg = parts[0]
    #     model = parts[1]
    #     serial_number = parts[2]
    #     send_freq = sensor_config["send-frequency"]

    #     data_dir = os.path.join(base_data_dir, mfg, model, serial_number)
    #     fname = f"{start_time.split('T')[0]}.jsonl"
    #     file = os.path.join(data_dir, fname)
    #     if not os.path.isfile(file):
    #         print(f"sensor not in flight: {sensor_config['sensor-id']}")
    #         return
        
    #     files = glob.glob(f"{data_dir}/*.jsonl")

    #     topic = "/".join(
    #         [
    #             config.mqtt_topic_prefix,
    #             "sensor",
    #             sensor_config["sensor-id"],
    #             "data",
    #             "update",
    #         ]
    #     )

    #     # add dimensions if necessary
    #     dimensions = {"time": 1}

    #     try:
    #         async with Client(config.mqtt_broker) as client:
    #             print(f"client: {client}, topic: {topic}")

    #             # for file in files:
    #                 # if os.path.basename(file) < "2023-07-18.jsonl":
    #                 #     continue
    #             with open(file, "r") as f:
    #                 for line in f:
    #                     try:
    #                         record = json.loads(line)
    #                     except Exception as e:
    #                         print(f"error: {e}, line={line}")
    #                         continue
                        
    #                     if record["variables"]["time"]["data"] < start_time:
    #                         continue
    #                     if record["variables"]["time"]["data"] >= end_time:
    #                         return

    #                     if "diameter" in record["variables"]:
    #                         if record["variables"]["diameter"]["data"] is None:
    #                             #    print(f"missing diameter: {record}")
    #                             continue
    #                         dp_dim = len(record["variables"]["diameter"]["data"])
    #                         if dp_dim > 0:
    #                             dimensions["diameter"] = dp_dim
    #                         else:
    #                             continue
    #                     # for n, v in record["variables"].items():
    #                     #     print(n,v)
    #                     #     if "shape" in v and len(v["shape"]) > 1:
    #                     #         for shape in v["shape"]:
    #                     #             print(shape, dimensions)
    #                     #             if shape not in dimensions:
    #                     #                 print(shape)
    #                     #                 if isinstance(v["data"], list):
    #                     #                     dimensions[shape] = len(v["data"])
    #                     #                     print(dimensions)
    #                     if isinstance(record["variables"]["time"], list):
    #                         dimensions["time"] = len(record["variables"]["time"])
    #                     record["dimensions"] = dimensions
    #                     # print(f"record: {record}")
    #                     # print(f"client: {client}, topic: {topic}")

    #                     msg_type = "sensor.data.update"
    #                     msg_source = "test-account.uas-test.envds"
    #                     attributes = {
    #                         "type": msg_type,
    #                         "source": msg_source,
    #                         "id": str(ULID()),
    #                         "datacontenttype": "application/json; charset=utf-8",
    #                     }
    #                     ce = CloudEvent(attributes=attributes, data=record)
    #                     # print(f"ce: {to_json(ce)}")
    #                     # await client.publish(topic, payload=json.dumps(record))
    #                     await client.publish(topic, payload=to_json(ce))  # , qos=2)
    #                     await asyncio.sleep(time_to_next(send_freq))
    #     except Exception as e:
    #         print(e)
    #         pass


    async def run(self):
        # self.client = Client(hostname=self.mqtt_config["hostname"])
        self.reconnect_interval = 1
        while self.do_run:
            try:
                # async with Client(hostname=self.mqtt_config["hostname"], client_id=self.client_id) as self.client:
                async with Client(hostname=self.config["hostname"], port=self.config["port"]) as self.client:
                    self.logger.debug("relay client:", extra={"client": self.client})
                # async with self.client:
                    # await self._subscribe_all()
                    self.logger.debug("relay client:", extra={"client": self.client})
                    # async with self.client.unfiltered_messages() as messages:
                    # async with self.client.messages() as messages:
                    self.connected = True
                    async for message in self.client.messages: #() as messages:
                        self.logger.debug("relay client:", extra={"payload": message})
                        # print(f"messages: {messages}")

                        # self.connected = True
                        
                        # async for message in messages:
                            # self.logger.debug(
                            #     "relay client - recv message",
                            #     extra={"topic": message.topic},
                            # )
                        if self.do_run:
                            # print(f"listen: {self.do_run}, {self.connected}")
                            self.logger.debug("relay client:", extra={"payload": from_json(message.payload)})
                            msg = Message(
                                data=from_json(message.payload),
                                source_path=message.topic,
                            )
                            # self.logger.debug(
                            #     "mqtt receive message:", extra={"data": msg.data}
                            # )
                           # await self.sub_data.put(msg)
                            self.logger.debug(
                                "relay client - recv message",
                                extra={
                                    "q": self.sub_data.qsize(),
                                    "payload": message.topic,
                                },
                            )
                            # print(
                            #     f"message received: {msg.data}"
                            #     # f"topic: {message.topic}, message: {message.payload.decode()}"
                            # )
                        else:
                            # print("close messages")
                            self.connected = False
                            # await messages.aclose()

                        # print(message.payload.decode())
                        # test_count += 1
            except MqttError as error:
                self.connected = False
                self.logger.error("relay client MqttError", extra={"error": error})
                # print(
                #     f'Error "{error}". Reconnecting sub in {self.reconnect_interval} seconds.'
                # )
                await asyncio.sleep(self.reconnect_interval)
            except Exception as e:
                self.logger.error("relay client - Exception", extra={"error": e})
                # print(e)
        # self.logger.info("relay client - done")
        # print("done with run")
        self.run_state = "SHUTDOWN"

    async def publisher(self):
        reconnect_interval = 5
        while self.do_run:
            print(f"publish: {self.do_run}, {self.connected}")
            if self.connected:
                msg = await self.pub_data.get()
                # print(f"msg = {msg}")
                # print(f"publisher:msg: {msg}")
                # print(f"msg: {msg.dest_path}")#, {to_json(msg.data)}")
                # print(f"msg: {msg.dest_path}, {to_json(msg.data)}")
                # print(msg.keys())
                # print(f"msg type: {type(msg.data)}")
                # bpayload = to_json(msg.data)
                # print(f"bpayload = {bpayload}")
                # payload = bpayload.decode()
                # print(f"payload = {payload}")
                try:
                    dest_path = msg.dest_path
                    if dest_path[0] != "/":
                        dest_path = f"/{dest_path}"
                    await self.client.publish(dest_path, payload=to_json(msg.data))
                    self.logger.debug("MQTT.publisher", extra={"dest_path": dest_path, "payload": to_json(msg.data), "client": self.client})
                    # await self.client.publish(msg.dest_path, payload=payload)
                except MqttError as error:
                    self.logger.error("relay client - MQTTError", extra={"error": error})
                
                await asyncio.sleep(.1)

            else:
                self.logger.debug(
                    "relay client",
                    extra={
                        "self.do_run": self.do_run,
                        "self.connected": self.connected,
                    },
                )
                await asyncio.sleep(1)
            # try:
            #     async with Client(self.mqtt_config["hostname"]) as client:
            #         while self.do_run:
            #             msg = await self.pub_data.get()
            #             await client.publish(msg.dest_path, payload=to_json(msg.data))
            #             # await self.client.publish(md.path, payload=to_json(md.payload))
            #             # await client.publish("measurements/instrument/trh/humidity", payload=json.dumps({"data": 45.1, "units": "%"}))
            #             # await client.publish("measurements/instrument/trh/temperature", payload=json.dumps({"data": 25.3, "units": "degC"}))
            #             # await client.publish("measurements/instrument/trh/pressure", payload=json.dumps({"data": 10013, "units": "Pa"}))
            #             # await client.publish("measurements/instruments/all", payload=json.dumps({"request": "status"}))
            #             # await client.publish("measurements/instrumentgroup/trhgroup", payload=json.dumps({"request": "stop"}))
            #             # await asyncio.sleep(1)
            # except MqttError as error:
            #     print(f'Error "{error}". Reconnecting pub in {reconnect_interval} seconds.')
            #     await asyncio.sleep(reconnect_interval)
        print("done with publisher")

    async def shutdown(self):
        self.do_run = False


class envdsRelay(envdsBase):
    """docstring for envdsRelay."""

    def __init__(self, config=None, **kwargs):
        super(envdsRelay, self).__init__(config, **kwargs)

        self.update_id("app_uid", "envds-relay")
        self.status.set_id_AppID(self.id)

        # self.logger = logging.getLogger(self.__class__.__name__)

        # self.file_map = dict()
        self.target_map = dict()

        
        # self.run_task_list.append(self._do_run_tasks())

    def configure(self):
        super(envdsRelay, self).configure()
        print("***here***")
        # get config from file
        try:
            with open("/app/config/relay.conf", "r") as f:
                conf = yaml.safe_load(f)
        except FileNotFoundError:
            conf = {}

        self.logger.debug("configure", extra={"self.conf": conf} )
      
        # TODO for target in conf, add to target_map and create relay client
        if "targets" in conf:
            for name, target in conf["targets"].items():
                if name in self.target_map:
                    if "client" in self.target_map and self.target_map["client"]:
                        del self.target_map["client"]
                        del self.target_map["config"]

                self.target_map[name]= {"config": dict()}
                self.target_map[name]["config"] = {
                    "hostname": target.get("uri", "localhost"),
                    "port": target.get("mqtt-port", 1883),
                    "target-namespace": target.get("target-namespace", "uasdaq"),
                    "datasystem-id-prefix": target.get("datasystem-id-prefix", "uas-base"),
                    "pub-data-buffer": asyncio.Queue(),
                    "sub-data-buffer": asyncio.Queue()
                }
                self.target_map[name]["client"] = MQTTRelayClient(
                    config=self.target_map[name]["config"]
                )


                    # close/delete relay client
                # self.target_map[name] = target
                # create relay client
                # add queues for pub/sub
        self.logger.debug("configure", extra={"self.target_map": self.target_map} )

    def run_setup(self):
        super().run_setup()

        self.logger = logging.getLogger(self.build_app_uid())
        self.update_id("app_uid", self.build_app_uid())

    def build_app_uid(self):
        parts = [
            "envds-relay",
            self.id.app_env_id,
        ]
        return (envdsRelay.ID_DELIM).join(parts)

    async def handle_data(self, message: Message):
        # print(f"handle_data: {message.data}")
        # self.logger.debug("handle_data", extra={"data": message.data})
        if message.data["type"] == bet.data_update():
            self.logger.debug(
                "handle_data",
                extra={
                    "type": bet.data_update(),
                    "data": message.data,
                    "source_path": message.source_path,
                },
            )

            src = message.data["source"]
            if src not in self.file_map:
                parts = src.split(".")
                sensor_name = parts[-1].split(self.ID_DELIM)
                # file_path = os.path.join("/data", "sensor", *sensor_name)

                # self.file_map[src] = DataFile(base_path=file_path)
                # await asyncio.sleep(1)
                # if self.file_map[src]:
                #     self.file_map[src].open()
                # await asyncio.sleep(1)
            # print(self.file_map[src].base_path)
            # await self.file_map[src].write_message(message)
            for name,target in self.target_map.items():
                try:
                    await target["config"]["pub-data-buffer"].put(message)
                except [KeyError, Exception]:
                    continue

            self.logger.debug("handle_data", extra={"payload": message})
            
    def set_routes(self, enable: bool=True):
        super(envdsRelay, self).set_routes(enable)

        topic_base = self.get_id_as_topic()

        print(f"set_routes: {enable}")

        self.set_route(
            # subscription=f"/envds/{self.id.app_env_id}/sensor/+/data/update",
            subscription=f"/envds/+/sensor/+/data/update",
            route_key=bet.data_update(),
            route=self.handle_data,
            enable=enable,
        )

        # if enable:
        #     self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
        #     self.router.register_route(key=bet.data_update(), route=self.handle_data)
        # else:
        #     self.message_client.unsubscribe(f"/envds/{self.id.app_env_id}/sensor/+/data/update")
        #     self.router.deregister_route(key=bet.data_update(), route=self.handle_data)
       
        # self.message_client.subscribe(f"{topic_base}/status/request")
        # self.router.register_route(key=det.status_request(), route=self.handle_status)
        # # self.router.register_route(key=et.status_update, route=self.handle_status)

        # self.router.register_route(key=et.control_request(), route=self.handle_control)
        # # self.router.register_route(key=et.control_update, route=self.handle_control)

    def run(self):
        print("run:1")
        super(envdsRelay, self).run()
        print("run:2")
        
        self.enable()

class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("test_task", extra={"test": "daq task"})


async def shutdown():
    print("shutting down")
    for task in task_list:
        print(f"cancel: {task}")
        task.cancel()


async def main(server_config: ServerConfig = None):
    # uiconfig = UIConfig(**config)
    if server_config is None:
        server_config = ServerConfig()
    print(server_config)

    print("starting daq test task")

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("envds-relay")

    print("main:1")
    relay = envdsRelay()
    print("main:2")
    relay.run()
    print("main:3")
    # await asyncio.sleep(2)
    # files.enable()
    # task_list.append(asyncio.create_task(files.run()))
    # await asyncio.sleep(2)

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # # print(LOGGING_CONFIG)
    # dict_config = {
    #     "version": 1,
    #     "disable_existing_loggers": False,
    #     "formatters": {
    #         "logfmt": {
    #             "()": "logfmter.Logfmter",
    #             "keys": ["at", "when", "name"],
    #             "mapping": {"at": "levelname", "when": "asctime"},
    #             "datefmt": get_datetime_format(),
    #         },
    #         "access": {
    #             "()": "uvicorn.logging.AccessFormatter",
    #             "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
    #             "use_colors": True,
    #         },
    #     },
    #     "handlers": {
    #         "console": {"class": "logging.StreamHandler", "formatter": "logfmt"},
    #         "access": {
    #             "formatter": "access",
    #             "class": "logging.StreamHandler",
    #             "stream": "ext://sys.stdout",
    #         },
    #     },
    #     "loggers": {
    #         "": {"handlers": ["console"], "level": "INFO"},
    #         "uvicorn.access": {
    #             "handlers": ["access"],
    #             "level": "INFO",
    #             "propagate": False,
    #         },
    #     },
    # }
    # logging.config.dictConfig(dict_config)

    # envdsLogger().init_logger()
    # logger = logging.getLogger("envds-daq")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))
    # logger.debug("starting envdsFiles")

    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/relay",
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    await server.serve()

    print("starting shutdown...")
    await shutdown()
    print("done.")


if __name__ == "__main__":

    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.path.dirname(os.path.abspath(__file__))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    print(sys.argv)
    config = ServerConfig()
    try:
        index = sys.argv.index("--host")
        host = sys.argv[index + 1]
        config.host = host
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--port")
        port = sys.argv[index + 1]
        config.port = int(port)
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--log_level")
        ll = sys.argv[index + 1]
        config.log_level = ll
    except (ValueError, IndexError):
        pass

    # print(LOGGING_CONFIG)

    # handler = logging.StreamHandler(sys.stdout)
    # formatter = Logfmter(
    #     keys=["at", "when", "name"],
    #     mapping={"at": "levelname", "when": "asctime"},
    #     datefmt=get_datetime_format()
    # )

    # # # self.logger = envdsLogger().get_logger(self.__class__.__name__)
    # # handler.setFormatter(formatter)
    # # # logging.basicConfig(handlers=[handler])
    # root_logger = logging.getLogger(__name__)
    # # # root_logger = logging.getLogger(self.__class__.__name__)
    # # # root_logger.addHandler(handler)
    # root_logger.addHandler(handler)
    # root_logger.setLevel(logging.INFO) # this should be settable
    # root_logger.info("in run", extra={"test": "value"})
    # print(root_logger.__dict__)

    # if "--host" in sys.argv:
    #     print(sys.argv.index("--host"))
    #     print(sys)
    asyncio.run(main(config))
