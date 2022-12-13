import os
import sys
import logging
import argparse
import asyncio
import signal
# import docker

try:
    import 
async def main(**kwargs):

    event_loop = asyncio.get_running_loop()

    # configure logging to stdout
    # isofmt = "%Y-%m-%dT%H:%M:%SZ"
    isofmt = get_datetime_format()
    # isofmt = get_datetime_format(fraction=True)
    logger = logging.getLogger()
    # root_logger.setLevel(logging.DEBUG)
    logger.setLevel(log_level)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # envds = DataSystem()
    envds = None

    def shutdown_handler(*args):
        envds.request_shutdown()

    event_loop.add_signal_handler(signal.SIGINT, shutdown_handler)
    event_loop.add_signal_handler(signal.SIGTERM, shutdown_handler)

    logger.debug("main: Started")

if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )
    # parser.add_argument("-h", "--host", help="set api host address")
    # parser.add_argument("-p", "--port", help="set api port number")
    # parser.add_argument("-n", "--name", help="set DataSystem name")

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    kwargs = dict()

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

    kwargs["log_level"] = log_level

    # if cl_args.host:
    #     kwargs["host"] = cl_args.host
    
    # if cl_args.port:
    #     kwargs["port"] = cl_args.port

    # if cl_args.name:
    #     kwargs["name"] = cl_args.name


    # set path
    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    # from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    # # from managers.hardware_manager import HardwareManager
    # # from envds.eventdata.eventdata import EventData
    # # from envds.eventdata.broker.broker import MQTTBroker

    asyncio.run(main(**kwargs))
    sys.exit()

    # # configure logging to stdout
    # isofmt = "%Y-%m-%dT%H:%M:%SZ"
    # # isofmt = get_datetime_format(fraction=True)
    # root_logger = logging.getLogger()
    # # root_logger.setLevel(logging.DEBUG)
    # root_logger.setLevel(log_level)
    # handler = logging.StreamHandler(sys.stdout)
    # formatter = logging.Formatter(
    #     "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt=isofmt
    # )
    # handler.setFormatter(formatter)
    # root_logger.addHandler(handler)

    # event_loop = asyncio.get_event_loop()

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

    # add services
    # services =
    #     [
    #         {
    #             "type": "service",
    #             "name": "datamanager",
    #             "namespace": "acg",
    #             "instance": {
    #                 "module": "envds.datamanager.datamanager",
    #                 "class": "envdsDataManager",
    #             },
    #         },
    #         {
    #             "type": "service",
    #             "name": "testdaq",
    #             "namespace": "acg",
    #             "instance": {"module": "envds.daq", "class": "envdsDAQ"},
    #         },
    #     ]

    envds = DataSystemManager(config=config)

    # create the DAQManager
    # daq_manager = DAQManager().configure(config=config)
    # if namespace is specified
    # daq_manager.set_namespace("junge")
    # daq_manager.set_msg_broker()
    # daq_manager.start()

    # task = event_loop.create_task(daq_manager.run())
    # task_list = asyncio.all_tasks(loop=event_loop)

    event_loop.add_signal_handler(signal.SIGINT, envds.request_shutdown)
    event_loop.add_signal_handler(signal.SIGTERM, envds.request_shutdown)

    event_loop.run_until_complete(envds.run())

    # try:
    #     event_loop.run_until_complete(daq_manager.run())
    # except KeyboardInterrupt:
    #     root_logger.info("Shutdown requested")
    #     event_loop.run_until_complete(daq_manager.shutdown())
    #     event_loop.run_forever()

    # finally:
    #     root_logger.info("Closing event loop")
    #     event_loop.close()

    # # from daq.manager.sys_manager import SysManager
    # # from daq.controller.controller import ControllerFactory  # , Controller
    # # from client.wsclient import WSClient
    # # import shared.utilities.util as util
    # # from shared.data.message import Message
    # # from shared.data.status import Status
    # # from shared.data.namespace import Namespace

