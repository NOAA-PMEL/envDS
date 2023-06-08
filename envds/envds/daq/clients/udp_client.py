import asyncio
from envds.daq.client import DAQClient, DAQClientConfig, _BaseClient
from envds.core import envdsStatus
from envds.exceptions import envdsRunTransitionException, envdsRunWaitException, envdsRunErrorException
import random
from anyio import create_connected_udp_socket, create_udp_socket, run
import socket
from envds.util.util import time_to_next


class _UDPClient(_BaseClient):
    """docstring for _TCPClient."""

    def __init__(self, config=None):
        # self.logger.debug("_TCPClient.init before super")
        super().__init__(config)

        self.logger.debug("_UDPClient.init")
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
        self.local_host = "0.0.0.0"
        self.local_port = 0
        self.remote_host = ""
        self.remote_port = 0
        # self.reconnect_delay = 1
        self.logger.debug("_UDPClient.init done")
        if "local-host" in self.config.properties:
            self.local_host = self.config.properties["local-host"]["data"]
        if "local-port" in self.config.properties:
            self.local_port = self.config.properties["local-port"]["data"]
        if "remote-host" in self.config.properties:
            self.remote_host = self.config.properties["remote-host"]["data"]
        if "remote-port" in self.config.properties:
            self.remote_port = self.config.properties["remote-port"]["data"]

        # self.send_method = send_method
        # self.read_method = read_method
        # self.read_terminator = read_terminator
        # self.read_num_bytes = read_num_bytes
        # self.decode_errors = decode_errors

        # self.return_packet_bytes = deque(maxlen=25000)

    def configure(self):
        super().configure()
        # parse self.config
        self.logger.debug("_UDPClient: configure", extra={"config": self.config.properties})
        # if "attributes" in self.config.properties:
        if "local-host" in self.config.properties:
            self.local_host = self.config.properties["local-host"]["data"]
        if "local-port" in self.config.properties:
            self.local_port = self.config.properties["local-port"]["data"]
        if "remote-host" in self.config.properties:
            self.remote_host = self.config.properties["remote-host"]["data"]
        if "remote-port" in self.config.properties:
            self.remote_port = self.config.properties["remote-port"]["data"]
        self.logger.debug("_UDPClient: configure", extra={"host": self.local_host, "port": self.local_port})


    # async def connection_monitor(self):

    #     while True:
    #         try:
    #             while self.keep_connected:

    #                 if self.connection_state == self.DISCONNECTED:
    #                     # connect
    #                     self.connection_state = self.CONNECTING
    #                     try:
    #                         self.logger.debug("open_connection", extra={"host": self.host, "port": self.port})
    #                         self.reader, self.writer = await asyncio.open_connection(
    #                             host=self.host,
    #                             port=self.port
    #                         )
    #                         self.logger.debug("_TCPClient: connect", extra={"host": self.host, "port": self.port} )
    #                         self.connection_state = self.CONNECTED
    #                     except (asyncio.TimeoutError, ConnectionRefusedError, Exception) as e:
    #                         self.logger.error("_TCPClient connection error", extra={"error": e})
    #                         self.reader = None
    #                         self.writer = None
    #                         self.connection_state = self.DISCONNECTED
    #                 await asyncio.sleep(self.reconnect_delay)

    #             await asyncio.sleep(self.reconnect_delay)            
    #         except Exception as e:
    #             self.logger.error("connection_monitor error", extra={"error": e})

    async def recv_data_loop(self):
        while True:
            try:
                print("here:1")
                async with await create_udp_socket(family=socket.AF_INET, local_host=self.local_host, local_port=self.local_port) as self.udp:
                    print(f"here:2 {self.udp}")
                    self.connected = True
                    async for packet, (host, port) in self.udp:
                        self.remote_host = host
                        self.remote_port = port
                        # print(f"udp: {packet.decode()}\naddress: {(host, port)}")
                        await self.recv_buffer.put(packet.decode())
                        await asyncio.sleep(.01)
                        # await udp.sendto(b'Hello, ' + packet, host, port)
                print("connection closed")
                await asyncio.sleep(1)
            except Exception as e:
                print("error: {e}")

            await asyncio.sleep(1)

    async def send_data_loop(self):
        while True:
            try:
                if self.connected and self.remote_host and self.remote_port > 0:
                    packet = await self.send_buffer.get()
                    await self.udp.send(packet.encode())
                    print("send message to udp")
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
        print("_UDPClient.enable")
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

class UDPClient(DAQClient):
    """docstring for TCPClient."""

    def __init__(self, config: DAQClientConfig=None, **kwargs):
        # print("mock_client: 1")
        super(UDPClient, self).__init__(config=config)
        # print("mock_client: 2")
        self.logger.debug("UDPClient.init")
        self.client_class = "_UDPClient"
        self.logger.debug("UDPClient.init", extra={"config": config})

        # TODO: set uid here? or let caller do it?
        self.config = config
        # print("mock_client: 3")

        # self.mock_type = "1D"  # 2D, i2c
        # self.read_method = "readline"
        # self.send_method = "ascii"
        # self.decode_errors = "strict"
        # self.read_terminator = "\r"
        # print("mock_client: 4")
        self.logger.debug("UDPClient.init", extra={'config': self.config})

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
        if self.enabled():
            data = await self.client.read()
            return data
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
