import asyncio
from envds.daq.client import DAQClient, DAQClientConfig, _BaseClient
from envds.core import envdsStatus
from envds.exceptions import envdsRunTransitionException
import random

class MockClient(DAQClient):
    """docstring for MockClient."""

    def __init__(self, config: DAQClientConfig=None, **kwargs):
        super(MockClient, self).__init__()

        # TODO: set uid here? or let caller do it?
        self.config = config

        self.mock_type = "1D"  # 2D, i2c
        self.read_method = "readline"

        class _MockClient(_BaseClient):
            """docstring for _MockClient."""

            def __init__(self):
                super(_MockClient, self).__init__()

                self.mock_data_type = "1D"

                # self.enable_task_list.append(self.connect())

            async def do_enable(self):
                try:
                    super(_MockClient, self).do_enable()
                except envdsRunTransitionException:
                    raise

                # simulate connect delay
                await asyncio.sleep(1)

                self.status.set_actual(envdsStatus.ENABLED, envdsStatus.TRUE)

            async def readline(self, decode_errors="strict"):
                if self.mock_type == "1D":
                    return self.mock_data_1D().decode(decode_errors=decode_errors)
                elif self.mock_type == "2D":
                    return self.mock_data_2D().decode(decode_errors=decode_errors)

            async def readbinary(self, num_bytes=1, decode_errors='strict'):
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

                data = ",".join(variables)
                return data.encode()

            def mock_data_2D(self):
                variables = []
                return "".encode()

            def mock_data_binary(self):
                variables = []
                return "".encode()

    async def recv_from_client(self):
        if self.enabled():
            if self.read_method == "readline":
                data = await self.client.readline()
                return data
            
        return None

    async def send_to_client(self, data):
        if self.enabled():
            print(f"mock client send: {data}")
