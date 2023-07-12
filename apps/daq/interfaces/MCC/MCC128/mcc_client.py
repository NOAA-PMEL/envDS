import asyncio
from envds.daq.client import DAQClient, DAQClientConfig, _BaseClient
from envds.core import envdsStatus
from envds.exceptions import envdsRunTransitionException, envdsRunWaitException, envdsRunErrorException
import random
from anyio import create_connected_udp_socket, create_udp_socket, run
import socket
from envds.util.util import time_to_next

from daqhats import hat_list, HatIDs, mcc128, AnalogInputMode, AnalogInputRange, OptionFlags
import numpy as np

class MCC128Board():
    
    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(MCC128Board, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        super().__init__()
        
        # self.recv_buffer = asyncio.Queue()

        self.recv_buffer = dict()

        print("init")
        board_list = hat_list(filter_by_id = HatIDs.ANY)
        if not board_list:
            self.board = None
        else:    
            for entry in board_list:
                if entry.id == HatIDs.MCC_128:
                    print("Board {}: MCC 128".format(entry.address))
                    self.board = mcc128(entry.address)
                    self.board.a_in_mode_write(AnalogInputMode.DIFF)
                    self.board.a_in_range_write(AnalogInputRange.BIP_1V)


    async def scan_start(self, channel: int, num_samples: int, sample_time: int):
        try:

            chan_list=[channel]
            for chan in chan_list:
                chan_mask |= 0x01 << chan
            
            self.board.a_in_scan_start(chan_mask, num_samples, sample_time, OptionFlags.DEFAULT)
            total_samples_read = 0
            timeout = sample_time*2
            read_result = self.board.a_in_scan_read_numpy(num_samples, timeout)
            total_samples_read += len(read_result.data)

            results = {
                "mean": np.mean(read_result.data, axis=0),
                "stdev": np.std(read_result.data, axis=0)
            }

            if channel not in self.recv_buffer:
                self.recv_buffer[channel] = asyncio.Queue()            
            await self.recv_buffer[channel].put(results)

        except Exception as e:
            print(f"scan_start error - {e}")

    async def scan_read(self, channel):
        if self.recv_buffer[0].empty():
            return None
        return await self.recv_buffer[0].get()

class _MCCClient(_BaseClient):
    """docstring for _TCPClient."""

    def __init__(self, config=None):
        # self.logger.debug("_TCPClient.init before super")
        super().__init__(config)

        self.logger.debug("_MCCClient.init")
        # self.mock_data_type = "1D"
        # print("_MockClient.init")
        self.connected = False
        self.keep_connected = False
        # self.run_task_list.append(self.connection_monitor())
        # self.enable_task_list.append(asyncio.create_task(asyncio.sleep(1)))
        self.enable_task_list.append(self.recv_data_loop())
        self.enable_task_list.append(self.send_data_loop())
        self.recv_buffer = asyncio.Queue()
        self.send_buffer = asyncio.Queue()

        # asyncio.create_task(self.connection_monitor())
        # self.host = "192.168.86.38"
        # self.port = 24
        # self.local_host = "0.0.0.0"
        # self.local_port = 0
        # self.remote_host = ""
        # self.remote_port = 0
        # # self.reconnect_delay = 1
        # self.logger.debug("_MCCClient.init done")
        # if "local-host" in self.config.properties:
        #     self.local_host = self.config.properties["local-host"]["data"]
        # if "local-port" in self.config.properties:
        #     self.local_port = self.config.properties["local-port"]["data"]
        # if "remote-host" in self.config.properties:
        #     self.remote_host = self.config.properties["remote-host"]["data"]
        # if "remote-port" in self.config.properties:
        #     self.remote_port = self.config.properties["remote-port"]["data"]

        self.channel = 0
        if "channel" in self.config.properties:
            self.channel = self.config.properties["channel"]["data"]

        # self.send_method = send_method
        # self.read_method = read_method
        # self.read_terminator = read_terminator
        # self.read_num_bytes = read_num_bytes
        # self.decode_errors = decode_errors

        # self.return_packet_bytes = deque(maxlen=25000)

        self.mcc128 = MCC128Board()

    def configure(self):
        super().configure()
        # parse self.config
        self.logger.debug("_MCCClient: configure", extra={"config": self.config.properties})
        # if "attributes" in self.config.properties:
        # if "local-host" in self.config.properties:
        #     self.local_host = self.config.properties["local-host"]["data"]
        # if "local-port" in self.config.properties:
        #     self.local_port = self.config.properties["local-port"]["data"]
        # if "remote-host" in self.config.properties:
        #     self.remote_host = self.config.properties["remote-host"]["data"]
        # if "remote-port" in self.config.properties:
        #     self.remote_port = self.config.properties["remote-port"]["data"]

        self.channel = 0
        if "channel" in self.config.properties:
            self.channel = self.config.properties["channel"]["data"]
        self.logger.debug("_MCCClient: configure", extra={"host": self.local_host, "port": self.local_port})

    async def recv_data_loop(self):
        while True:
            try:
                data = await self.mcc128.scan_read(channel=self.channel)
                if data:
                    await self.recv_buffer.put(data)
                await asyncio.sleep(.1)
            except Exception as e:
                print("error: {e}")
                await asyncio.sleep(1)

            await asyncio.sleep(.1)

    async def send_data_loop(self):
        while True:
            try:
                data = await self.send_buffer.get()

                if self.connected and self.mcc128.board:
                    if "num_samples" in data and "sample_time" in data:    
                        self.mcc128.board.scan_start(
                            channel=self.channel, 
                            num_samples=data["num_samples"],
                            sample_time=data["sample_time"]
                        )    
                await asyncio.sleep(.1)
            except Exception as e:
                print("error: {e}")
            await asyncio.sleep(.1)

    async def read(self):
        return await self.recv_buffer.get()

    async def write(self, data: str):
        await self.send_buffer.put(data)

    async def do_enable(self):
        try:
            await super().do_enable()
        # except envdsRunTransitionException:
        except (envdsRunTransitionException, envdsRunErrorException, envdsRunWaitException) as e:
            raise e
        print("_MCCClient.enable")
        # simulate connect delay
        await asyncio.sleep(1)
        self.keep_connected = True
        
        # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)


# async def do_run(self):
#     try:
#         self.client = getattr(self, "_MockClient")()
#         # self.client = self._MockClient
#         self.logger.debug("do_run", extra={"client": self.client})
#     except Exception as e:
#         self.logger.error("do_run", extra={"error": e})
#     await super().do_run()

class MCCClient(DAQClient):
    """docstring for TCPClient."""

    def __init__(self, config: DAQClientConfig=None, **kwargs):
        # print("mock_client: 1")
        super(MCCClient, self).__init__(config=config)
        # print("mock_client: 2")
        self.logger.debug("MCCClient.init")
        self.client_class = "MCCClient"
        self.logger.debug("MCCClient.init", extra={"config": config})

        # TODO: set uid here? or let caller do it?
        self.config = config
        # print("mock_client: 3")

        # self.mock_type = "1D"  # 2D, i2c
        # self.read_method = "readline"
        # self.send_method = "ascii"
        # self.decode_errors = "strict"
        # self.read_terminator = "\r"
        # print("mock_client: 4")
        self.logger.debug("MCCClient.init", extra={'config': self.config})

        # self.enable_task_list.append(self.recv_loop())
        # self.enable_task_list.append(self.send_loop())

        # self.logger.debug("init", extra={})
        # try:
        #     self.client = _MockClient()
        # except Exception as e:
        #     self.logger.error("init client error", extra={"error": e})
        #     self.client = None
        # self.logger.debug("init", extra={"client": self.client})


    async def recv_from_client(self):
        # print("recv_from_client:1")
        # if self.enabled():
        if True:
            try:
                print(f"recv_from_client:1 { self.client}")
                
                data = await self.client.read()
                print(f"recv_from_client:2 {data}")
                return data
            except Exception as e:
                self.logger.error("recv_from_client error", extra={"e": e})
            # props = self.config.properties["sensor-interface-properties"]["read-properties"]

            # read_method = props.get("read-method", self.read_method)
            # decode_errors = props.get("decode-errors", self.decode_errors)


            # # print(f"recv_from_client:2 -- readmethod={self.read_method}")
            # if self.read_method == "readline":
            #     # print("recv_from_client:3")
            #     data = await self.client.readline()
            #     print(f"recv_from_client:4 {data}")

            # elif read_method == "read_until":
            #     data = await self.client.read_until(
            #         terminator=props.get("read-terminator",self.read_terminator), 
            #         decode_errors=decode_errors) 

            # elif read_method == "readbytes":
            #     data = await self.client.read(
            #         num_bytes=props.get("read-num-bytes",1),
            #         decode_errors=decode_errors
            #     )
            # elif read_method == "readbinary":
            #     ret_packet_size = await self.client.get_return_packet_size()
            #     data = await self.client.readbinary(
            #         num_bytes=ret_packet_size,
            #         decode_errors=decode_errors
            #     )

            # return data
        
        # print("recv_from_client:5")
        return None

    async def send_to_client(self, data):
        try:
            
            num_samples = data["ad-command"].get("num_samples", 1)             num_samples = data["ad-command"].get("num_samples", 1)            
            sample_time = data["ad-command"].get("sample_time", 100)             num_samples = data["ad-command"].get("num_samples", 1)            
            
            await self.client.write(data)

            # send_method = data.get("send-method", self.send_method)
            
            # if send_method == "binary":
            #     # if num of expected bytes not supplied, fail
            #     try:
            #         read_num_bytes = data["read-num-bytes"]
            #         self.client.return_packet_bytes.append(
            #             data["read-num-bytes"]
            #         )
            #         await self.client.writebinary(data["data"])
            #     except KeyError:
            #         self.logger.error("binary write failed - read-num-bytes not specified")
            #         return
            # else:
            #     try:
            #         await self.client.write(data["data"])
            #     except KeyError:
            #         self.logger.error("write failed - data not specified")
            #         return

            # self.logger.debug(
            #     "send_to_client",
            #     extra={
            #         "send_method": send_method,
            #         "data": data["data"]
            #     },
            # )
        except Exception as e:
            self.logger.error("send_to_client error", extra={"error": e})
