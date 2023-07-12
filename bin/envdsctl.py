import sys
import os
import asyncio
import argparse
import logging


if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest="command")

    apply = subparser.add_parser("apply")
    apply.add_argument("-f", "--file")
    apply.add_argument("-ns", "--namespace")


    namespace = subparser.add_parser("namespace")
    add_parser = namespace.add_subparsers(dest="ns_cmd")
    ns_add = add_parser.add_parser("add")
    ns_add.add_argument("ns_name")
    # service = subparser.add_parser("service")
    # manage = subparser.add_parser("manage")
    # controller = subparser.add_parser("controller")
    # instrument = subparser.add_parser("instrument")

    # ns_sub = namespace.add_subparsers(dest="ns_cmd")
    # ns_sub.
    # namespace.add_argument("add", type=str, help="add namespace")
    # namespace.add_argument("remove", help="remove namespace")

    # service.add_argument("add", help="add namespace")
    # service.add_argument("remove", help="remove namespace")
    # service.add_argument("start", help="remove namespace")
    # service.add_argument("stop", help="remove namespace")
    # svc_sub = service.add_subparsers(dest="svc_command")
    # svc_ns = svc_sub.add_parser("-ns","--namespace")

    # namespace.add_argument("remove", help="remove namespace")
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    if cl_args.command == "apply":
        cmd = ["envdsctl apply"]
        if cl_args.file:
            cmd.append(f"-f {cl_args.file}")
            # print(f"envdsctl apply -f {cl_args.file}")
        else:
            print("error")

        if cl_args.namespace:
            cmd.append(f"-ns {cl_args.namespace}")

        print(f"{' '.join(cmd)}")
    elif cl_args.command == "namespace":
        if cl_args.ns_cmd == "add":
            print(f"adding namespace: {cl_args.ns_name}")
            # print(f"add: {cl_args.add}")
        # print(cl_args.add)
        # if cl_args.add:
        #     print(cl_args.add)

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
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    # print(sys.path, BASE_DIR)

    # from envds.envds.envds import envdsBase
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
