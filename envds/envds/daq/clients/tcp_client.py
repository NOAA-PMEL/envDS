import asyncio
from envds.daq.client import DAQClient, DAQClientConfig, _StreamClient
from envds.core import envdsStatus
from envds.exceptions import envdsRunTransitionException, envdsRunWaitException, envdsRunErrorException
import random

from envds.util.util import time_to_next

class _TCPClient(_StreamClient):
    """docstring for _TCPClient."""

    def __init__(self, config=None):
        # self.logger.debug("_TCPClient.init before super")
        super().__init__(config)

        self.logger.debug("_TCPClient.init")
        # self.mock_data_type = "1D"
        # print("_MockClient.init")
        self.enable_task_list.append(self.connection_monitor())
        # self.enable_task_list.append(asyncio.create_task(asyncio.sleep(1)))
        self.connected = False
        self.keep_connected = False

        self.host = "192.168.86.46"
        self.port = 23
        self.reconnect_delay = 1
        self.logger.debug("_TCPClient.init done")

        # self.send_method = send_method
        # self.read_method = read_method
        # self.read_terminator = read_terminator
        # self.read_num_bytes = read_num_bytes
        # self.decode_errors = decode_errors

        # self.return_packet_bytes = deque(maxlen=25000)

    def configure(self):
        super().configure()
        # parse self.config
        self.logger.debug("_TCPClient: configure")
        if "attributes" in self.config.properties:
            if "host" in self.config.properties["attributes"]:
                self.host = self.config.properties["attributes"]["host"]["data"]
            if "port" in self.config.properties["attributes"]:
                self.port = self.config.properties["attributes"]["port"]["data"]
            self.logger.debug("_TCPClient: configure", extra={"host": self.host, "port": self.port})


    async def connection_monitor(self):

        while True:

            while self.keep_connected:

                if self.connection_state == self.DISCONNECTED:
                    # connect
                    self.connection_state = self.CONNECTING
                    try:
                        self.reader, self.writer = await asyncio.open_connection(
                            host=self.host,
                            port=self.port
                        )
                        self.logger.debug("_TCPClient: connect", extra={"host": self.host, "port": self.port} )
                        self.connection_state = self.CONNECTED
                    except (asyncio.TimeoutError, ConnectionRefusedError) as e:
                        self.logger.error("_TCPClient connection error", extra={"error": e})
                        self.reader = None
                        self.writer = None
                        self.connection_state = self.DISCONNECTED
                await asyncio.sleep(self.reconnect_delay)
            await asyncio.sleep(self.reconnect_delay)            
            
    async def do_enable(self):
        try:
            await super().do_enable()
        # except envdsRunTransitionException:
        except (envdsRunTransitionException, envdsRunErrorException, envdsRunWaitException) as e:
            raise e
        print("_TCPlient.enable")
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

class TCPClient(DAQClient):
    """docstring for TCPClient."""

    def __init__(self, config: DAQClientConfig=None, **kwargs):
        # print("mock_client: 1")
        super(TCPClient, self).__init__(config=config)
        # print("mock_client: 2")
        self.logger.debug("TCPClient.init")
        self.client_class = "_TCPClient"
        self.logger.debug("TCPClient.init", extra={"config": config})

        # TODO: set uid here? or let caller do it?
        self.config = config
        # print("mock_client: 3")

        # self.mock_type = "1D"  # 2D, i2c
        self.read_method = "readline"
        # print("mock_client: 4")
        self.logger.debug("TCPClient.init", extra={'config': self.config})

        # self.enable_task_list.append(self.recv_loop())

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
            props = self.config.properties["sensor-interface-properties"]["read-properties"]

            read_method = props.get("read-method", self.read_method)
            decode_errors = props.get("decode-errors", self.decode_errors)


            # print(f"recv_from_client:2 -- readmethod={self.read_method}")
            if self.read_method == "readline":
                # print("recv_from_client:3")
                data = await self.client.readline()
                print(f"recv_from_client:4 {data}")

            elif read_method == "read_until":
                data = await self.client.read_until(
                    terminator=props.get("read-terminator",self.read_terminator), 
                    decode_errors=decode_errors) 

            elif read_method == "readbytes":
                data = await self.client.read(
                    num_bytes=props.get("read-num-bytes",1),
                    decode_errors=decode_errors
                )
            elif read_method == "readbinary":
                ret_packet_size = await self.client.get_return_packet_size()
                data = await self.client.readbinary(
                    num_bytes=ret_packet_size,
                    decode_errors=decode_errors
                )

            return data
        
        # print("recv_from_client:5")
        return None

    async def send_to_client(self, data):
        if self.enabled():
            try:
                
                send_method = data.get("send-method", self.send_method)
                
                if send_method == "binary":
                    # if num of expected bytes not supplied, fail
                    try:
                        read_num_bytes = data["read-num-bytes"]
                        self.client.return_packet_bytes.append(
                            data["read-num-bytes"]
                        )
                        await self.client.writebinary(data["data"])
                    except KeyError:
                        self.logger.error("binary write failed - read-num-bytes not specified")
                        return
                else:
                    try:
                        await self.client.write(data["data"])
                    except KeyError:
                        self.logger.error("write failed - data not specified")
                        return

                self.logger.debug(
                    "send_to_client",
                    extra={
                        "send_method": send_method,
                        "data": data["data"]
                    },
                )
            except Exception as e:
                self.logger.error("send_to_client error", extra={"error": e})
