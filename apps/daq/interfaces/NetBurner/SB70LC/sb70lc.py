import asyncio
import signal
import sys
import os
import logging
import logging.config
import yaml
from envds.core import envdsLogger
from envds.daq.interface import Interface, InterfaceConfig #, InterfacePath
from envds.daq.event import DAQEvent

from pydantic import BaseModel


task_list = []

class SB70LC(Interface):
    """docstring for SB70LC."""

    metadata = {
        "attributes": {
            # "name": {"type"mock1",
            "type": {"type": "char", "data": "NetBurner"},
            "name": {"type": "char", "data": "SB70LC"},
            "host": {"type": "char", "data": "localhost"},
            "description": {
                "type": "char",
                "data": "Netburner SB70LC serial to ethernet server with i2c",
            },
            "tags": {"type": "char", "data": "testing, netburner, SB70LC, serial, tcp, ethernet, i2c, sensor"},
        },
        "paths": {
            "port-1": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 23},
                },
                "data": [],
            },
            "port-2": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 24},
                },
                "data": [],
            },
            "port-I2C": {
                "attributes": {
                    "client_module": {"type": "string", "data": "envds.daq.clients.tcp_client"},
                    "client_class": {"type": "string", "data": "TCPClient"},
                    "host": {"type": "string", "data": "localhost"},
                    "port": {"type": "int", "data": 26},
                },
                "data": [],
            },
        }
    }

    def __init__(self, config=None, **kwargs):
        # print("mock:1")
        super(SB70LC, self).__init__(config=config, **kwargs)
        # print("mock:2")
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_client_module = "envds.daq.clients.tcp_client"
        self.default_client_class = "TCPClient"

        self.data_loop_task = None

    def configure(self):

        # print("configure:1")
        super(SB70LC, self).configure()

        try:
            # get config from file
            # print("configure:2")
            try:
                # print("configure:3")
                with open("/app/config/interface.conf", "r") as f:
                    conf = yaml.safe_load(f)
                # print("configure:4")
            except FileNotFoundError:
                conf = {"uid": "UNKNOWN", "paths": {}}

            # add hosts to each path if not present
            try:
                host = conf["host"]
            except KeyError as e:
                self.logger.debug("no host - default to localhost")
                host = "localhost"
            for name, path in conf["paths"].items():
                if "host" not in path:
                    path["host"] = host

            # print("configure:5")
            self.logger.debug("conf", extra={"data": conf})

            atts = SB70LC.metadata["attributes"]

            # print("configure:7")
            path_map = dict()
            for name, val in SB70LC.metadata["paths"].items():
                # path_map[name] = InterfacePath(name=name, path=val["data"])
                # print("configure:8")

                if "client_module" not in val["attributes"]:
                    val["attributes"]["client_module"]["data"] = self.default_client_module
                if "client_class" not in val["attributes"]:
                    val["attributes"]["client_class"]["data"] = self.default_client_class
                # print("configure:9")

                # set path host from interface attributes
                if "host" in atts:
                    val["attributes"]["host"]["data"] = atts["host"]

                client_config = val
                # override values from yaml config
                if "paths" in conf and name in conf["paths"]:
                    self.logger.debug("yaml conf", extra={"id": name, "conf['paths']": conf['paths'], })
                    for attname, attval in conf["paths"][name].items():
                        self.logger.debug("config paths", extra={"id": name, "attname": attname, "attval": attval})
                        client_config["attributes"][attname]["data"] = attval
                # print("configure:10")
                self.logger.debug("config paths", extra={"client_config": client_config})
                    
                path_map[name] = {
                    "client_id": name,
                    "client": None,
                    "client_config": client_config,
                    "client_module": val["attributes"]["client_module"]["data"],
                    "client_class": val["attributes"]["client_class"]["data"],
                    # "data_buffer": asyncio.Queue(),
                    "recv_handler": self.recv_data_loop(name),
                    "recv_task": None,
                }
            # print("configure:11")

            self.config = InterfaceConfig(
                type=atts["type"]["data"],
                name=atts["name"]["data"],
                uid=conf["uid"],
                paths=path_map
            )
            # print(f"self.config: {self.config}")

            self.logger.debug(
                "configure",
                extra={"conf": conf, "self.config": self.config},
            )
        except Exception as e:
            self.logger.debug("sb70lc:configure", extra={"error": e})
 
    def package_i2c_data(self, data: dict):

        '''
        example: 
            {
                "i2c-command": "read-buffer",
                "address": "44",
                "read-length": 6,
                "delay-ms": 50 # 50ms in seconds
            }
        '''
        # all hex values as hex strings
        try:
            print(f"package_i2c_data: {data}")
            # for command in data["i2c-commands"]:
            i2c_command = data["i2c-command"] 
            address = data["address"]
            # write_data = data["data"]

            delay = data.get("delay-ms", 0) / 1000.0

            if i2c_command == "write-byte":
                write_data = data["data"]
                output = f'#WB{address}{write_data}\n'

            elif i2c_command == "write-buffer":
                write_data = data["data"]
                write_length = data.get(
                    "write-length",
                    len(bytes.fromhex(write_data))
                )
                length = f"{write_length:02}"
                output = f'#WW{address}{length}{write_data}\n'

            elif i2c_command == "read-byte":
                output = f'#RB{address}\n'

            elif i2c_command == "read-buffer":
                if "read-length" not in data:
                    # self.logger.error("No read-length specified for i2c read-buffer")
                    return None, delay
                read_length = data["read-length"]
                length = f"{read_length:02}"                
                output = f'#RR{address}{length}\n'

            outdata = {"data": output, "delay": delay}
            print(f"package_i2c_data: {output},{delay}")
            return outdata
        
        except KeyError as e:
            print(f"package_i2c_data error: {e}")
            # return None, None
            return None

    def unpack_i2c_data(self, data):

        self.logger.debug("unpack_i2c_data", extra={"data": data})
        print(f"unpack_data_type: {type(data)}")
        try:
            if not data: # or data == "OK":
                return None
            elif isinstance(data["data"], str):
                print(f"check_for_ok: {data['data'].strip()}, {data['data'].strip() == 'OK'}")
                if data['data'].strip() == "OK":
                    return None
            return data
        except KeyError:
            return None
        
    async def recv_data_loop(self, client_id: str):
        
        # self.logger.debug("recv_data_loop", extra={"client_id": client_id})
        while True:
            try:
                # client = self.config.paths[client_id]["client"]
                client = self.client_map[client_id]["client"]
                # while client is not None:
                if client:
                    self.logger.debug("recv_data_loop", extra={"client": client})
                    data = await client.recv()
                    self.logger.debug("recv_data", extra={"client_id": client_id, "data": data})

                    if client_id == "port-I2C":
                        data = self.unpack_i2c_data(data)
                        if data is None:
                            continue
                        self.logger.debug("port-I2C", extra={"data": data})

                    await self.update_recv_data(client_id=client_id, data=data)
                    # await asyncio.sleep(self.min_recv_delay)
                else:
                    await asyncio.sleep(1)
            except (KeyError, Exception) as e:
                self.logger.error("recv_data_loop", extra={"error": e})
                await asyncio.sleep(1)

            # await asyncio.sleep(self.min_recv_delay)
            await asyncio.sleep(0.1)

    async def wait_for_ok(self, timeout=0):
        pass

    async def send_data(self, event: DAQEvent):

            try:
                print(f"send_data:1 - {event}")
                client_id = event["path_id"]
                client = self.client_map[client_id]["client"]
                data = event.data["data"]

                if client_id == "port-I2C":
                    if "i2c-commands" in data["data"]:
                        for command in data["data"]["i2c-commands"]:
                            print(f"command: {command}")
                            # i2c_data, delay = self.package_i2c_data(command)
                            i2c_data = self.package_i2c_data(command)
                            print(f"i2c: {i2c_data['data']}, {i2c_data['delay']}")
                            if i2c_data:
                                # await self.wait_for_ok(timeout=i2c_data["delay"])
                                await asyncio.sleep(i2c_data['delay'])
                                await client.send(i2c_data)
                    else:
                        await client.send(data)

                    # wrap data in netburner protocol for i2c
                    # might need special client class for this?
                else:
                    await client.send(data)
            except KeyError:
                pass

class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("sb70lc_test_task", extra={"test": "sb70lc task"})


async def shutdown(interface):
    print("shutting down")

    if interface:
        await interface.shutdown()

    for task in task_list:
        print(f"cancel: {task}")
        task.cancel()


async def main(server_config: ServerConfig = None):
    # uiconfig = UIConfig(**config)
    if server_config is None:
        server_config = ServerConfig()
    print(server_config)

    # print("starting mock1 test task")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("interface::sb70lc:nb73")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    iface = SB70LC()
    iface.run()
    # task_list.append(asyncio.create_task(iface.run()))
    # await asyncio.sleep(2)
    iface.enable()
    logger.debug("Starting SB70LC Interface")

    # remove fastapi ----
    # # get config from file
    # uid = "9999"
    # try:
    #     with open("/app/config/interface.conf", "r") as f:
    #         conf = yaml.safe_load(f)
    #         try:
    #             uid = conf["uid"]
    #         except KeyError:
    #             pass
    # except FileNotFoundError:
    #     pass

    # root_path=f"/envds/interface/system/Mock/{uid}"
    # # print(f"root_path: {root_path}")

    # config = uvicorn.Config(
    #     "main:app",
    #     host=server_config.host,
    #     port=server_config.port,
    #     log_level=server_config.log_level,
    #     root_path=root_path,
    #     # log_config=dict_config,
    # )

    # server = uvicorn.Server(config)
    # # test = logging.getLogger()
    # # test.info("test")
    # await server.serve()
    # ----

    event_loop = asyncio.get_event_loop()
    global do_run 
    do_run = True
    def shutdown_handler(*args):
        global do_run
        do_run = False

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    while do_run:
        logger.debug("sb70lc.run", extra={"do_run": do_run})
        await asyncio.sleep(1)


    print("starting shutdown...")
    # await iface.shutdown()
    await shutdown(iface)
    # await asyncio.sleep(2)
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

    asyncio.run(main(config))
