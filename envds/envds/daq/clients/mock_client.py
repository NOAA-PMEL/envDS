import asyncio
from envds.daq.client import DAQClient, DAQClientConfig, _StreamClient
from envds.core import envdsStatus
from envds.exceptions import (
    envdsRunTransitionException,
    envdsRunWaitException,
    envdsRunErrorException,
)
import random

from envds.util.util import time_to_next


class _MockClient(_StreamClient):
    """docstring for _MockClient."""

    def __init__(self, config=None):
        super().__init__(config)

        self.mock_data_type = "1D"
        # print("_MockClient.init")
        # self.enable_task_list.append(self.connect())
        # self.enable_task_list.append(asyncio.create_task(asyncio.sleep(1)))

    async def do_enable(self):
        try:
            await super().do_enable()
        # except envdsRunTransitionException:
        except (
            envdsRunTransitionException,
            envdsRunErrorException,
            envdsRunWaitException,
        ) as e:
            raise e
        print("_Mockclient.enable")
        # simulate connect delay
        await asyncio.sleep(1)

        # self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)

    async def readline(self, decode_errors="strict"):
        # print("readline")
        try:
            if self.mock_data_type == "1D":
                data = self.mock_data_1D().decode(errors=decode_errors)
                # print(f"data: {data}")
                return self.mock_data_1D().decode(errors=decode_errors)
            elif self.mock_data_type == "2D":
                return self.mock_data_2D().decode(errors=decode_errors)
        except Exception as e:
            print(f"readline error: {e}")

        return None

    async def readbinary(self, num_bytes=1, decode_errors="strict"):
        return self.mock_data_binary()

    def mock_data_1D(self):
        variables = []
        # variables["temperature"] = str(round(25 + random.uniform(-3, 3), 3))
        # variables["rh"] = str(round(60 + random.uniform(-5, 5), 3))
        # variables["pressure"] = str(round(1000 + random.uniform(-5, 5), 3))
        # variables["wind_speed"] = str(round(10 + random.uniform(-5, 5), 3))
        # variables["wind_direction"] = str(round(90 + random.uniform(-20, 20), 3))

        variables.append(str(round(25 + random.uniform(-3, 3), 3)))
        variables.append(str(round(60 + random.uniform(-5, 5), 3)))
        variables.append(str(round(1000 + random.uniform(-5, 5), 3)))
        variables.append(str(round(10 + random.uniform(-5, 5), 3)))
        variables.append(str(round(90 + random.uniform(-20, 20), 3)))
        variables.append(str(round(2 + random.uniform(-0.1, 0.1), 3)))

        data = ",".join(variables)
        # print(f"_MockClient.1D: {data}")
        return data.encode()

    def mock_data_2D(self):
        variables = []
        return "".encode()

    def mock_data_binary(self):
        variables = []
        return "".encode()


# async def do_run(self):
#     try:
#         self.client = getattr(self, "_MockClient")()
#         # self.client = self._MockClient
#         self.logger.debug("do_run", extra={"client": self.client})
#     except Exception as e:
#         self.logger.error("do_run", extra={"error": e})
#     await super().do_run()


class MockClient(DAQClient):
    """docstring for MockClient."""

    def __init__(self, config: DAQClientConfig = None, **kwargs):
        # print("mock_client: 1")
        super(MockClient, self).__init__(config=config)
        # print("mock_client: 2")

        self.client_class = "_MockClient"

        # TODO: set uid here? or let caller do it?
        self.config = config
        # print("mock_client: 3")

        self.mock_type = "1D"  # 2D, i2c
        self.read_method = "readline"
        self.send_method = "ascii"
        self.read_terminator = "\n"
        self.decode_errors = "strict"
        
        # print("mock_client: 4")

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
            # print(f"recv_from_client:2 -- readmethod={self.read_method}")
            props = self.config.properties["sensor-interface-properties"]["read-properties"]
            # try:
            #     read_method = props["read-method"]
            # except KeyError:
            #     read_method = self.read_method
            read_method = props.get("read-method", self.read_method)

            # try:
            #     decode_errors = props["decode-errors"]
            # except KeyError:
            #     decode_errors = self.decode_errors
            decode_errors = props.get("decode-errors", self.decode_errors)

            if read_method == "readline":
                # print("recv_from_client:3")
                data = await self.client.readline(decode_errors=decode_errors)
                print(f"recv_from_client:4 {data}")

                # simulate 1 sec data
                await asyncio.sleep(time_to_next(1))
                return data

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
                # send_method = "ascii"
                # try:
                #     send_method = data["send-method"]
                # except KeyError:
                #     pass
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
