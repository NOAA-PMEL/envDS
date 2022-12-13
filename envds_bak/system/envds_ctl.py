import sys
import os
import asyncio
import argparse
import logging

# conditional imports
# print(__name__)
# if __name__ != "__main__":
from envds.message.message import Message, MessageBrokerClient
from envds.util.util import get_datetime, get_datetime_string, datetime_mod_sec
from envds.system.envds import envdsBase
# else:
from envds import envdsBase

class envdsCTL(envdsBase):
    '''
    Command line interface/control management tool envDS. Patterned after kubectl
    '''
    def __init__(self, config=None, **kwargs) -> None:
        super().__init__(config=config, **kwargs)

    def set_config(self, config=None):
        return super().set_config(config=config)

    async def run(self):

        if not await self.wait_for_message_client():
            self.do_run = False
        
        if self.config:
            if 

        # if self.do_run:
        #     self.apply_subscriptions(self.default_subscriptions)

            # remove for debug
            # start required services
            await self.create_required_services()

        do_shutdown_req = False
        while self.do_run:
            # extra = {"channel": "envds/system/status"}
            # status = Message.create(
            #     source=self.envds_id,
            #     type=envdsEvent.get_type(type=envdsEvent.TYPE_STATUS, action=envdsEvent.TYPE_ACTION_UPDATE),
            #     data={"update": "ping"},
            #     **extra,
            # )
            if get_datetime().second % 10 == 0:

                status = self.create_status_update({"status": {"value": "OK"}})
                await self.send_message(status)
                do_shutdown_req = True
            # self.loop.create_task(self.send_message(status))

            await asyncio.sleep(1)
            if do_shutdown_req:
                # self.request_shutdown()
                do_shutdown_req = False

        self.logger.info("envDS shutdown.")
        self.run_status = "SHUTDOWN"
        # return await super().run()

if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )
    subparser = parser.add_subparsers(dest="command")

    namespace = subparser.add_parser("namespace")
    service = subparser.add_parser("service")
    manage = subparser.add_parser("manage")
    controller = subparser.add_parser("controller")
    instrument = subparser.add_parser("instrument")

    namespace.add_argument("add", help="add namespace")
    namespace.add_argument("remove", help="remove namespace")

    service.add_argument("add", help="add namespace")
    service.add_argument("remove", help="remove namespace")
    service.add_argument("start", help="remove namespace")
    service.add_argument("stop", help="remove namespace")
    svc_sub = service.add_subparsers(dest="svc_command")
    svc_ns = svc_sub.add_parser("-ns","--namespace", default="default")

    # namespace.add_argument("remove", help="remove namespace")


    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    log_level = logging.INFO
    if cl_args.log_level:
        level = cl_args.log_level
        if level == "WARN":
            log_level = logging.WARN
        elif level == "ERROR":
            log_level = logging.ERROR
        elif log_level == "DEBUG":
            log_level = logging.DEBUG
        elif log_level == "CRITICAL":
            log_level = logging.CRITICAL

    if cl_args.debug:
        log_level = logging.DEBUG

    # set path
    BASE_DIR = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    from envds.system.envds import envdsBase
    from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

   # configure logging to stdout
    isofmt = "%Y-%m-%dT%H:%M:%SZ"
    # isofmt = get_datetime_format(fraction=True)
    root_logger = logging.getLogger()
    # root_logger.setLevel(logging.DEBUG)
    root_logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    event_loop = asyncio.get_event_loop()

    config = {
        # "namespace": "gov.noaa.pmel.acg",
        "message_broker": {
            "client": {
                "instance": {
                    "module": "envds.message.message",
                    "class": "MQTTBrokerClient",
                }
            },
            "config": {
                "host": "localhost",
                "port": 1883,
                # "keepalive": 60,
                "ssl_context": None,
                # "ssl_client_cert": None,
                # ne
            },
        },
    }
