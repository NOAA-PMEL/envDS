import asyncio
import signal
# from cloudevents.http import from_http
from cloudevents.conversion import from_http
from cloudevents.pydantic import CloudEvent

# from typing import Union
from pydantic import BaseModel

from envds.core import envdsBase, envdsAppID
from envds.event.types import BaseEventType as et


class envdsRegistry(envdsBase):
  """docstring for envdsRegistry."""
  def __init__(self):
    super(envdsRegistry, self).__init__()

    # self.id["name"] = "registry"
    self.id.app_class = "registry"
    print(self.id)

    self._registry = dict()
    self._monitoring = dict()

    self._setup()

    asyncio.create_task(self.run())

  def configure(self):
      # path = self.message_client.get_path_from_id(self.get_id())
      self.message_client.subscribe(f"+/+/+/{et.TYPE_STATUS}/{et.ACTION_UPDATE}")
      self.router.register_route(key=et.status_update, route=self.handle_status)
      # self.router.register_route(key=et.status_update, route=self.handle_status)

      self.router.register_route(key=et.control_request, route=self.handle_control)
      # self.router.register_route(key=et.control_update, route=self.handle_control)

  def _setup(self):
      self.message_client.subscribe("sensor/all")
      self.message_client.subscribe("sensor/instrument/trh/#")
      self.message_client.subscribe("sensor/instruments/all")
      self.message_client.subscribe("sensor/instrumentgroup/trhgroup/#")

async def main():

    event_loop = asyncio.get_running_loop()

    app = envdsRegistry()

    do_run = True
    while app.do_run:

        def shutdown_handler(*args):
            # print(f"shutting down client: {client}")
            print(f"signal caught: {args}, shutting down client")
            # client.request_shutdown()
            asyncio.create_task(app.shutdown())
            # pub_client.request_shutdown()
            do_run = False

        event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
        event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)
        await asyncio.sleep(1)
       
    print("done")


if __name__ == "__main__":
    asyncio.run(main())