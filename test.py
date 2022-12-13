#!/usr/bin/env python
# from datetime import datetime
# import sys

# print("hello world")
# print(datetime.utcnow())
# print(sys.version_info)
# print(sys.path)

import asyncio
import json
import signal
# from asyncio_mqtt import Client, MqttError
# from cloudevents.http import CloudEvent, from_dict, from_json, to_structured
# from cloudevents.conversion import to_json#, from_dict, from_json#, to_structured
# from cloudevents.exceptions import InvalidStructuredJSON

# from envds.message.message import Message
# from envds.message.client import MessageClientManager
# from envds.event.event import envdsEvent

# from envds.core import envdsBase

# import aioredis
import redis.asyncio as redis
from redis.commands.json.path import Path
from datetime import datetime
import random

# class TestApp2(envdsBase):
#     def __init__(self):
#         super(TestApp2, self).__init__()

#         self.task_list = []
#         self.do_run = True

#         self.task_list.append(asyncio.create_task(self.publish()))
#         self.task_list.append(asyncio.create_task(self.run()))
#         self._setup()
#         asyncio.create_task(self.run())
        
#     def _setup(self):
#         self.message_client.subscribe("sensor/all")
#         self.message_client.subscribe("sensor/instrument/trh/#")
#         self.message_client.subscribe("sensor/instruments/all")
#         self.message_client.subscribe("sensor/instrumentgroup/trhgroup/#")

#     async def publish(self):
#         # while pub_client:
#         # pub_client = MessageClientManager.create()
#         while self.do_run:

#             # attributes = {
#             #     "type": "com.example.sampletype1",
#             #     "source": "https://example.com/event-producer",
#             # }
#             data = {"data": 45.1, "units": "%"}
#             event = envdsEvent.create_data_update(source="test/app", data=data)
#             msg = Message(dest_path="sensor/instrument/trh/humidity", data=event)
#             # event = CloudEvent(attributes, data)
#             await self.message_client.send(msg)
#             data = {"data": 24.3, "units": "degC"}
#             event = envdsEvent.create_data_update(source="test/app", data=data)
#             msg = Message(dest_path="sensor/instrument/trh/temperature", data=event)
#             # event = CloudEvent(attributes, data)
#             await self.message_client.send(msg)
#             await asyncio.sleep(1)
        
#         # pub_client.request_shutdown()


# class TestApp(object):
#     """docstring for TestClient."""
#     def __init__(self):
#         super(TestApp, self).__init__()

#         # self.client = None
#         # self.message = None
#         # self.reconnect_interval = 5
#         # self.client_ready = False
#         self.task_list = []
#         self.do_run = True

#         self.task_list.append(asyncio.create_task(self.publish()))
#         self.task_list.append(asyncio.create_task(self.run()))
#     # def subscribe(self, topic: str):
#     #     asyncio.create_task(self._subscribe(topic))
        
#     # async def _subscribe(self, topic: str):
#     #     while self.client is None or not self.client_ready:
#     #         await asyncio.sleep(1) # wait for client to be ready

#     #     await self.client.subscribe(topic)
        
#     # def unsubscribe(self, topic: str):
#     #     asyncio.create_task(self._unsubscribe(topic))

#     # async def _unsubscribe(self, topic: str):
        
#     #     while self.client is None or not self.client_ready:
#     #         await asyncio.sleep(1) # wait for client to be ready

#     #     await self.client.subscribe(topic)

#     async def publish(self):
#         # while pub_client:
#         pub_client = MessageClientManager.create()
#         while self.do_run:

#             # attributes = {
#             #     "type": "com.example.sampletype1",
#             #     "source": "https://example.com/event-producer",
#             # }
#             data = {"data": 45.1, "units": "%"}
#             event = envdsEvent.create_data_update(source="test/app", data=data)
#             msg = Message(dest_path="measurements/instrument/trh/humidity", data=event)
#             # event = CloudEvent(attributes, data)
#             await pub_client.send(msg)
#             await asyncio.sleep(1)
        
#         pub_client.request_shutdown()
        
#     async def run(self):

#         client = MessageClientManager.create()
#         # client.start()

#         client.subscribe("measurements/all")
#         client.subscribe("measurements/instrument/trh/#")
#         client.subscribe("measurements/instruments/all")
#         client.subscribe("measurements/instrumentgroup/trhgroup/#")

#         while self.do_run:

#             msg = await client.get()
#             print(f"message: {msg.source_path}: {msg.data}")


#             # try:
#             #     async with Client("localhost") as client:

#             #         async with client.unfiltered_messages() as messages:

#             #             self.client_ready = True
#             #             async for message in messages:
#             #                 if self.do_run:
#             #                     # data = from_dict(json.loads(message.payload.decode()))
#             #                     data = from_json(message.payload.decode())
#             #                     print(f"topic: {message.topic}, message: {data}")
#             #                     # print(f"topic: {message.topic}, message: {message.payload.decode()}")
#             #                 else:
#             #                     print("close messages")
#             #                     # self.client_ready = False
#             #                     await messages.aclose()

#             #                 # print(message.payload.decode())
#             #                 # test_count += 1
#             # except MqttError as error:
#             #     # self.client_ready = False
#             #     print(f'Error "{error}". Reconnecting sub in {self.reconnect_interval} seconds.')
#             #     await asyncio.sleep(self.reconnect_interval)

#         client.request_shutdown()

#     async def shutdown(self):
#         # self.client.disconnect()
#         # await self.messages.aclose()
#         self.do_run = False

# async def publish(pub_client):
#     # event_loop = asyncio.get_running_loop()
#     # reconnect_interval = 5
#     # pub_client = MessageClientManager.create()
#     # pub_client.start()
#     # pub_client.run()

#     # do_run = True
#     # def shutdown_handler(*args):
#     #     # print(f"shutting down client: {client}")
#     #     print(f"signal caught: {args}, shutting down client")
#     #     asyncio.create_task(pub_client.shutdown())
#     #     # do_run = False

#     # event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
#     # event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

#     # while pub_client.do_run:
#     while pub_client:

#         # attributes = {
#         #     "type": "com.example.sampletype1",
#         #     "source": "https://example.com/event-producer",
#         # }
#         data = {"data": 45.1, "units": "%"}
#         event = envdsEvent.create_data_update(source="test/app", data=data)
#         msg = Message(dest_path="measurements/instrument/trh/humidity", data=event)
#         # event = CloudEvent(attributes, data)
#         await pub_client.send(msg)
#         await asyncio.sleep(1)


# async def print_messages(messages, template):
#     async for message in messages:
#         print(template.format(message.payload))

# async def cancel_tasks(tasks):
#     for task in tasks:
#         if task.done():
#             continue
#         try:
#             task.cancel()
#             await task
#         except asyncio.CancelledError:
#             pass

async def main():

    event_loop = asyncio.get_running_loop()

    # app = TestApp2()

    # app.client.subscribe("measurements/all")
    # app.client.subscribe("measurements/instrument/trh/#")
    # client.subscribe("measurements/instruments/all")
    # client.subscribe("measurements/instrumentgroup/trhgroup/#")

    r = redis.from_url("redis://localhost")
    # r = redis.Redis(host="localhost", port=6379)#, db="test-registry")
    index = 0
    while True:
        val1 = random.random()
        val2 = random.random()
        # print(f"{index}, {val}")

        record = {
            "time": datetime.utcnow().isoformat(),
            "temperature": val1,
            "rh": val2
        }
        await r.json().set(f"{index}", Path.root_path(), record)
        await r.expire(f"{index}", time=60)
        # await r.set(f"{index}", f"{val}", ex=60)
        # bin_value = await r.get(f"{index}") 
        # assert bin_value == b"string-value"
        # r = redis.from_url("redis://localhost", decode_responses=True)
        output = await r.json().get(f"{index}") 
        # assert str_value == "string-value"
        print(output)
        index += 1
        await asyncio.sleep(1)
    await r.close()


    # do_run = True
    # while app.do_run:

    #     def shutdown_handler(*args):
    #         # print(f"shutting down client: {client}")
    #         print(f"signal caught: {args}, shutting down client")
    #         # client.request_shutdown()
    #         asyncio.create_task(app.shutdown())
    #         # pub_client.request_shutdown()
    #         do_run = False

    #     event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    #     event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)
    #     await asyncio.sleep(1)
       
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
