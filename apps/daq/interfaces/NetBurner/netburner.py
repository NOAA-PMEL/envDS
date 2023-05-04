import asyncio
import signal
import sys
import os
import logging
import logging.config
import yaml
from envds.core import envdsLogger
from envds.daq.interface import Interface, InterfaceConfig #, InterfacePath

from pydantic import BaseModel

from envds.envds.daq.event import DAQEvent

task_list = []

class NetBurner(Interface):
    """docstring for NetBurner."""

    metadata = {}

    def __init__(self, config=None, **kwargs):
        # print("mock:1")
        super(NetBurner, self).__init__(config=config, **kwargs)
        # print("mock:2")
        self.data_task = None
        self.data_rate = 1
        # self.configure()

        self.default_client_module = "envds.daq.clients.tcp_client"
        self.default_client_class = "TCPClient"

        self.data_loop_task = None

    def configure(self):

        # print("configure:1")
        super(NetBurner, self).configure()

        try:
            # get config from file
            # print("configure:2")
            try:
                # print("configure:3")
                with open("/app/config/interface.conf", "r") as f:
                    conf = yaml.safe_load(f)
                # print("configure:4")
            except FileNotFoundError:
                conf = {"uid": "UNKNOWN", "paths": {}}

            # add hosts to each path if not present
            try:
                host = conf["host"]
            except KeyError as e:
                self.logger.debug("no host - default to localhost")
                host = "localhost"
            for name, path in conf["paths"].items():
                if "host" not in path:
                    path["host"] = host

            # print("configure:5")
            self.logger.debug("conf", extra={"data": conf})

            atts = NetBurner.metadata["attributes"]

            # print("configure:7")
            path_map = dict()
            for name, val in NetBurner.metadata["paths"].items():
                # path_map[name] = InterfacePath(name=name, path=val["data"])
                # print("configure:8")

                if "client_module" not in val["attributes"]:
                    val["attributes"]["client_module"]["data"] = self.default_client_module
                if "client_class" not in val["attributes"]:
                    val["attributes"]["client_class"]["data"] = self.default_client_class
                # print("configure:9")

                # set path host from interface attributes
                if "host" in atts:
                    val["attributes"]["host"]["data"] = atts["host"]

                client_config = val
                # override values from yaml config
                if "paths" in conf and name in conf["paths"]:
                    self.logger.debug("yaml conf", extra={"id": name, "conf['paths']": conf['paths'], })
                    for attname, attval in conf["paths"][name].items():
                        self.logger.debug("config paths", extra={"id": name, "attname": attname, "attval": attval})
                        client_config["attributes"][attname]["data"] = attval
                # print("configure:10")
                self.logger.debug("config paths", extra={"client_config": client_config})
                    
                path_map[name] = {
                    "client_id": name,
                    "client": None,
                    "client_config": client_config,
                    "client_module": val["attributes"]["client_module"]["data"],
                    "client_class": val["attributes"]["client_class"]["data"],
                    # "data_buffer": asyncio.Queue(),
                    "recv_handler": self.recv_data_loop(name),
                    "recv_task": None,
                }
            # print("configure:11")

            self.config = InterfaceConfig(
                type=atts["type"]["data"],
                name=atts["name"]["data"],
                uid=conf["uid"],
                paths=path_map
            )
            # print(f"self.config: {self.config}")

            self.logger.debug(
                "configure",
                extra={"conf": conf, "self.config": self.config},
            )
        except Exception as e:
            self.logger.debug(f"{self.__class__.__name__}:configure", extra={"error": e})



    

    