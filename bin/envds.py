import os
import sys
import logging
import argparse
import asyncio
import signal

# from envds.daq.daq import DAQSystem
# from envds.envds.envds import DataSystem

if __name__ == "__main__":

    print(f"args: {sys.argv[1:]}")

    # parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-l", "--log-level", help="set logging level")
    parser.add_argument(
        "-d", "--debug", help="show debugging output", action="store_true"
    )

    cl_args = parser.parse_args()
    # if cl_args.help:
    #     # print(args.help)
    #     exit()

    log_level = logging.DEBUG
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
    # BASE_DIR = os.path.dirname(
    #     os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # )
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    # from envds.envds.envds import DataSystemManager
    from envds.envds.envds import DataSystem

    # from envds.message.message import Message
    from envds.util.util import get_datetime, get_datetime_string, get_datetime_format

    # from managers.hardware_manager import HardwareManager
    # from envds.eventdata.eventdata import EventData
    # from envds.eventdata.broker.broker import MQTTBroker

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

    envds_config = {
        "apiVersion": "envds/v1",
        "kind": "DataSystem",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            "namespace": "envds",
        },
        "spec": {
            # "class": {
            #     "module": "envds.daq.daq",
            #     "class":  "DAQSystem"
            # },
            "broker": {  # <- insert full broker spec here. will be done if omitted
                "apiVersion": "envds/v1",
                "kind": "envdsBroker",
                "metadata": {
                    "name": "default",
                    # "namespace": "envds" # will pick up default
                },
                "spec": {
                    "type": "MQTT",
                    "host": "localhost",
                    "port": 1883,
                    "protocol": "TCP",
                },
            }
        },
    }

    broker_config = {
        "apiVersion": "envds/v1",
        "kind": "envdsBroker",
        "metadata": {
            "name": "default",
            # "namespace": "envds" # will pick up default
        },
        "spec": {"type": "MQTT", "host": "localhost", "port": 1883, "protocol": "TCP"},
    }

    reg_config = {
        "apiVersion": "envds/v1",
        "kind": "Registry",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            # "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.registry.registry", "class": "envdsRegistry"},
        },
    }

    datamanager_config = {
        "apiVersion": "envds/v1",
        "kind": "DataManager",
        "metadata": {
            "name": "who-daq",  # <- this has to be unique name in namespace
            # "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.data.data", "class": "envdsDataManager"},
            "basePath": "/home/Data/envDS/",
            "save-to-file": True,
            # "meta-data": ??,
            # "data-server": ??,
        },
    }


    daq_config = {
        "apiVersion": "envds/v1",
        "kind": "DAQSystem",
        "metadata": {
            "name": "daq-test",  # <- this has to be unique name in namespace
            "namespace": "acg-test",
            # "part-of": {"kind": "DataSystem", "name": "who-daq"},
        },
        "spec": {
            "class": {"module": "envds.daq.daq", "class": "DAQSystem"},
            # "broker": { # <- insert full broker spec here. will be done if omitted
            #     "apiVersion": "envds/v1",
            #     "kind": "envdsBroker",
            #     "metadata": {
            #         "name": "default",
            #         # "namespace": "envds" # will pick up default
            #     },
            #     "spec": {
            #         "type": "MQTT",
            #         "host": "localhost",
            #         "port": 1883,
            #         "protocol": "TCP"
            #     }
            # }
        },
    }

    controller_config = {
        "apiVersion": "envds/v1",
        "kind": "DAQController",
        "metadata": {
            "name": "controller-test",  # <- this has to be unique name in namespace
            "namespace": "acg-test",
            "labels": {
                "part-of": {
                    "kind": "DAQSystem",
                    "name": "daq-test",  # does this need to ref type (e.g., DAQSystem)?
                }
            },
        },
        "spec": {"class": {"module": "envds.daq.controller", "class": "DAQController"}},
    }

    envds_config_other = [
        # { # envds namespace
        #     "apiVersion": "envds/v1",
        #     "kind": "Namespace",
        #     "metadata": {
        #         "name": "envds"
        #     }
        # },
        {  # message broker
            "apiVersion": "envds/v1",
            "kind": "envdsBroker",
            "metadata": {
                "name": "default",
                # "namespace": "envds" # will pick up default
            },
            "spec": {
                "type": "MQTT",
                "host": "localhost",
                "ports": [{"name": "mqtt", "port": 1883, "protocol": "TCP"}],
            },
        },
        {
            "apiVersion": "envds/v1",
            "kind": "envdsBrokerClient",
            "metadata": {
                "name": "mqtt-client",
                "instance": "mqtt-client-system",
                "namespace": "envds",
                "labels": {"part-of": "envds.sys"},
            },
            "spec": {
                "class": {
                    "module": "envds.message.message",
                    "class": "MQTTBrokerClient",
                }
            },
        },
    ]

    config = {
        # "namespace": "gov.noaa.pmel.acg",
        "message_broker": {
            "name": "mqtt-broker",
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
        "services": {
            "daq_test": {
                "type": "service",
                "name": "daq-test",
                "namespace": "acg",
                "instance": {"module": "envds.daq.daq", "class": "DAQSystem",},
                "part-of": "envds.system",
            }
        },
    }

    # config = {
    #     # "namespace": "gov.noaa.pmel.acg",
    #     "message_broker": {
    #         "name": "mqtt-broker"
    #         "client": {
    #             "instance": {
    #                 "module": "envds.message.message",
    #                 "class": "MQTTBrokerClient",
    #             }
    #         },
    #         "config": {
    #             "host": "localhost",
    #             "port": 1883,
    #             # "keepalive": 60,
    #             "ssl_context": None,
    #             # "ssl_client_cert": None,
    #             # ne
    #         },
    #     },
    #     "required-services": {
    #         "registry": {
    #             "apiVersion": "evnds/v1",
    #             "kind": "service",
    #             "metadata": {
    #                 "name": "registry"
    #             }
    #             "spec": {
    #                 "template": {
    #                     "spec": {
    #                         "instance": {
    #                             "module": "envds.registry.registry",
    #                             "class": "envdsRegistry",
    #                         }
    #                     }
    #                 }
    #             }
    #         }
    #     }

    #     "services": {
    #         "daq-test": {
    #             "apiVersion": "evnds/v1",
    #             "kind": "service",
    #             "metadata": {
    #                 "name": "daq-test"
    #             }
    #             "spec": {
    #                 "template": {
    #                     "spec": {
    #                         "instance": {
    #                             "module": "envds.daq.daq",
    #                             "class": "DAQSystem",
    #                         }
    #                     }
    #                 }
    #             }
    #             "type": "service",
    #             "name": "daq-test",
    #             "namespace": "acg",
    #             "instance": {
    #                 "module": "envds.daq.daq",
    #                 "class": "DAQSystem",
    #             },
    #             "part-of": "envds.system",
    #         }
    #     }
    # }

    # add services

    # daq_config = {
    #     "type": "service",
    #     "name": "daq-test",
    #     "namespace": "acg",
    #     "instance": {"module": "envds.daq", "class": "DAQSystem",},
    #     "part-of": "envds.system",
    # }

    # add services

    # daq_config = {
    #     "type": "service",
    #     "name": "daq-test",
    #     "namespace": "acg",
    #     "instance": {"module": "envds.daq", "class": "DAQSystem",},
    #     "part-of": "envds.system",
    # }

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

    example = {
        "apiVersion": "envds/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "daq-main",
            "namespace": "acg",
            "labels": {
                "app": "daqmanager",
                # "role": "type of role", # used if replicas>1?
                # "tier": "backend"
            },
        },
        "spec": {  # specification or desired state of object
            # "replicas": 1 # unneeded for our app
            # "selector": { # used if replicas>1?
            #     "matchLabels": {
            #         "app": "daq-manager"
            #     }
            # }
            "template": {  # how to create the object
                "metadata": {"labels": {"app": "daqmanager"}},
                "spec": {
                    # if using containers, this would be "container"
                    # "containers": [
                    #     {
                    #         "name": "container name"
                    #     }
                    # ]
                    # for envds - no sidecars
                    "envdsApp": {
                        "module": "envds.daq",
                        "class": "DAQSystem",
                        "resources": {},
                        "ports": [],
                    }
                },
            }
        },
    }

    # from https://kubernetes.io/docs/tutorials/stateless-application/guestbook/
    kub_deployment_example = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {
            "name": "redis-leader",
            "labels": {"app": "redis", "role": "leader", "tier": "backend"},
        },
        "spec": {
            "replicas": 1,
            "selector": {"matchLabels": {"app": "redis"}},
            "template": {
                "metadata": {
                    "labels": {"app": "redis", "role": "leader", "tier": "backend"}
                },
                "spec": {
                    "containers": [  # allows for sidecar containers
                        {
                            "name": "leader",
                            "image": "docker.io/redis:6.0.5",
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "100Mi"}
                            },
                            "ports": [{"containerPort": 6379}],
                        }
                    ]
                },
            },
        },
    }

    kub_service_example = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {
            "name": "redis-leader",
            "labels": {"app": "redis", "role": "leader", "tier": "backend"},
        },
        "spec": {
            "ports": [{"port": 6379, "targetPort": 6379}],
            "selector": {"app": "redis", "role": "leader", "tier": "backend"},
        },
    }

    kub_fe_deployment_example = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "frontend"},
        "spec": {
            "replicas": 3,
            "selector": {"matchLabels": {"app": "guestbook", "tier": "frontend"}},
            "template": {
                "metadata": {"labels": {"app": "guestbook", "tier": "frontend"}},
                "spec": {
                    "containers": [
                        {
                            "name": "php-redis",
                            "image": "gcr.io/google_samples/gb-frontend:v5",
                            "env": [{"name": "GET_HOSTS_FROM", "value": "dns"}],
                            "resources": {
                                "requests": {"cpu": "100m", "memory": "100Mi"}
                            },
                            "ports": [{"containerPort": 80}],
                        }
                    ]
                },
            },
        },
    }

    # envds = DataSystemManager(config=config)
    # envds = DataSystem(config=broker_config)
    envds = DataSystem(config=envds_config)
    envds.apply_nowait(config=daq_config)
    envds.apply_nowait(config=datamanager_config)
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
