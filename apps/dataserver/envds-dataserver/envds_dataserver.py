import asyncio
import glob
from typing import Tuple
import uvicorn
from uvicorn.config import LOGGING_CONFIG
import httpx
import sys
import os
import json
import logging
from logfmter import Logfmter
import logging.config
from pydantic import BaseSettings, Field
from envds.core import envdsBase, envdsLogger
from envds.util.util import (
    get_datetime_format,
    time_to_next,
    get_datetime,
    get_datetime_string,
)

# from envds.message.message import Message
from envds.message.message import Message
from cloudevents.http import CloudEvent, from_dict, from_json
from cloudevents.conversion import to_json, to_structured
from envds.event.event import envdsEvent, EventRouter
from envds.event.types import BaseEventType as bet

from envds.daq.sensor import Sensor

from envds.daq.db import (
    SensorTypeRegistration,
    SensorRegistration,
    init_db_models,
    register_sensor_type,
    register_sensor,
    get_sensor_type_registration,
    get_sensor_registration,
    get_all_sensor_registration,
    get_sensor_registration_by_pk,
    get_all_sensor_type_registration,
    get_sensor_type_registration_by_pk,
)

# from typing import Union

from pydantic import BaseModel
from jinja2 import Environment, PackageLoader, select_autoescape, FileSystemLoader

task_list = []


class Dataserver:
    def __init__(
        self,
        base_path="/data",
        save_interval=60,
        file_interval="day",
        # config=None,
    ):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.base_path = base_path

        # unless specified, flush file every 60 sec
        self.save_interval = save_interval

        # allow for cases where we want hour files
        #   options: 'day', 'hour'
        self.file_interval = file_interval

        # if config:
        #     self.setup(config)

        # if self.base_path[-1] != '/':
        #     self.base_path += '/'

        self.save_now = True
        # if save_interval == 0:
        #     self.save_now = True

        self.current_file_name = ""

        self.data_buffer = asyncio.Queue()

        self.task_list = []
        self.loop = asyncio.get_event_loop()

        self.file = None

        self.open()

    async def write_message(self, message: Message):
        # print(f"write_message: {message}")
        # print(f"write_message: {message.data}")
        # print(f'{msg.to_json()}')
        await self.write(message.data)
        # if 'body' in msg and 'DATA' in msg['body']:
        #     await self.write(msg['body']['DATA'])

    async def write(self, data_event: CloudEvent):
        # add message to queue and return
        # print(f'write: {data}')
        # print(f"write: {data_event}")
        await self.data_buffer.put(data_event.data)
        qsize = self.data_buffer.qsize()
        if qsize > 5:
            self.logger.warn("write buffer filling up", extra={"qsize": qsize})

    async def __write(self):

        while True:

            data = await self.data_buffer.get()
            # print(f'datafile.__write: {data}')

            try:
                dts = data["variables"]["time"]["data"]
                d_and_t = dts.split("T")
                ymd = d_and_t[0]
                hour = d_and_t[1].split(":")[0]
                # print(f"__write: {dts}, {ymd}, {hour}")
                self.__open(ymd, hour=hour)
                if not self.file:
                    return

                json.dump(data, self.file)
                self.file.write("\n")

                if self.save_now:
                    self.file.flush()
                    if self.save_interval > 0:
                        self.save_now = False

            except KeyError:
                pass

            # if data and ('DATA' in data):
            #     d_and_t = data['DATA']['DATETIME'].split('T')
            #     ymd = d_and_t[0]
            #     hour = d_and_t[1].split(':')[0]

            #     self.__open(ymd, hour=hour)

            #     if not self.file:
            #         return

            #     json.dump(data, self.file)
            #     self.file.write('\n')

            #     if self.save_now:
            #         self.file.flush()
            #         if self.save_interval > 0:
            #             self.save_now = False

    def __open(self, ymd, hour=None):

        fname = ymd
        if self.file_interval == "hour":
            fname += "_" + hour
        fname += ".jsonl"

        # print(f"__open: {self.file}")
        if (
            self.file is not None
            and not self.file.closed
            and os.path.basename(self.file.name) == fname
        ):
            return

        # TODO: change to raise error so __write can catch it
        try:
            # print(f"base_path: {self.base_path}")
            if not os.path.exists(self.base_path):
                os.makedirs(self.base_path, exist_ok=True)
        except OSError as e:
            self.logger.error("OSError", extra={"error": e})
            # print(f'OSError: {e}')
            self.file = None
            return
        # print(f"self.file: before")
        self.file = open(
            # self.base_path+fname,
            os.path.join(self.base_path, fname),
            mode="a",
        )
        self.logger.debug(
            "_open",
            extra={"file": self.file, "base_path": self.base_path, "fname": fname},
        )
        # print(f"open: {self.file}, {self.base_path}, {fname}")

    def open(self):
        self.logger.debug("DataFile.open")
        self.task_list.append(asyncio.create_task(self.save_file_loop()))
        self.task_list.append(asyncio.create_task(self.__write()))

    def close(self):

        for t in self.task_list:
            t.cancel()

        if self.file:
            try:
                self.file.flush()
                self.file.close()
                self.file = None
            except ValueError:
                self.logger.info("file already closed")
                # print("file already closed")

    async def save_file_loop(self):

        while True:
            if self.save_interval > 0:
                await asyncio.sleep(time_to_next(self.save_interval))
                self.save_now = True
            else:
                self.save_now = True
                await asyncio.sleep(1)


class envdsDataserver(envdsBase):
    """docstring for envdsFiles."""

    def __init__(self, config=None, **kwargs):
        super(envdsDataserver, self).__init__(config, **kwargs)

        self.update_id("app_uid", "envds-dataserver")
        self.status.set_id_AppID(self.id)

        # self.logger = logging.getLogger(self.__class__.__name__)

        # self.file_map = dict()

        # self.run_task_list.append(self._do_run_tasks())

        self.data_registry = dict()

        self.insert_buffer = asyncio.Queue()
        self.registry_buffer = asyncio.Queue()
        self.holding_buffer = asyncio.Queue(maxsize=100)

        self.run_task_list.append(self.check_registration_loop())
        self.run_task_list.append(self.check_holding_loop())
        self.run_task_list.append(self.erddap_insert_loop())

        # with open("/datasets.d/testfile.txt", "w") as f:
        #     print(f"f: {f}")
        #     f.write(f"hello world\n")
        #     print(f"f: {f}")

    def configure(self):
        super(envdsDataserver, self).configure()

        # self.message_client.subscribe(f"/envds/{self.id.app_env_id}/sensor/+/update")
        # self.router.register_route(key=bet.data_update(), route=self.handle_data)

    def run_setup(self):
        super().run_setup()

        self.logger = logging.getLogger(self.build_app_uid())
        self.update_id("app_uid", self.build_app_uid())

    def build_app_uid(self):
        parts = [
            "envds",
            "dataserver",
            self.id.app_env_id,
        ]
        return (envdsDataserver.ID_DELIM).join(parts)

    async def handle_data(self, message: Message):
        # print(f"handle_data: {message.data}")
        # self.logger.debug("handle_data", extra={"data": message.data})
        if message.data["type"] == bet.data_update():
            self.logger.debug(
                "handle_data",
                extra={
                    "type": bet.data_update(),
                    "data": message.data,
                    "source_path": message.source_path,
                },
            )
            # await self.insert_buffer.put(message)
            await self.registry_buffer.put(message)
            # src = message.data["source"]
            # parts = src.split(".")
            # sensor_name = parts[-1].split(Sensor.ID_DELIM)

    def set_routes(self, enable: bool = True):
        super(envdsDataserver, self).set_routes(enable)

        topic_base = self.get_id_as_topic()

        print(f"set_routes: {enable}")

        if enable:
            self.message_client.subscribe(
                f"/envds/{self.id.app_env_id}/sensor/+/data/update"
            )
            self.router.register_route(key=bet.data_update(), route=self.handle_data)
        else:
            self.message_client.unsubscribe(
                f"/envds/{self.id.app_env_id}/sensor/+/data/update"
            )
            self.router.deregister_route(key=bet.data_update(), route=self.handle_data)

    async def check_holding_loop(self):

        while True:

            hold_time, message = await self.holding_buffer.get()

            # check how long message has been on hold:
            #   <10s: keep holding
            #   10s - 1hr: retry
            #   >1hr: discard
            delta = get_datetime() - hold_time
            if delta > 10 and delta < 3600:  # how will it ever past 10s?
                await self.registry_buffer.put(message)
            if delta >= 3600:
                pass
            else:
                await self.holding_buffer.put((hold_time, message))

            await asyncio.sleep(0.1)

    async def create_config_file(
        self, dataset_id: str, metadata: dict
    ):  # attributes: dict, variables: dict) -> bool:

        # print(f"metadata: {metadata}")
        if metadata:
            attributes = metadata["attributes"]
            variables = metadata["variables"]
        else:
            return False

        env = Environment(
            # loader=PackageLoader("envds-dataserver"), autoescape=select_autoescape()
            loader=FileSystemLoader("templates/"),
            autoescape=select_autoescape(),
        )

        template = env.get_template("Make_Model_Version_dataset.xml")
        var_template = env.get_template("Make_Model_Version_variable.xml")
        vars = []

        try:
            erddap_version = f'v{attributes["format_version"]["data"].split(".")[0]}'
            make = attributes["make"]["data"]
            model = attributes["model"]["data"]
            erddap_version = f'v{attributes["format_version"]["data"].split(".")[0]}'
            # version = attributes["format_version"]["data"]
            ds_context = {
                "make": make,
                "model": model,
                "erddap_version": erddap_version,
                "version": attributes["format_version"]["data"],
            }
            if "description" in attributes:
                ds_context["description"] = attributes["description"]["data"]

            for name, variable in variables.items():

                if name == "time":
                    continue

                var_context = dict()
                var_context["source_name"] = name
                var_context["destination_name"] = name
                var_context["data_type"] = variable["type"]

                # missing_value = "NaN"
                # if variable["type"] == "int":
                #     missing_value = "NaN"
                # elif variable["type"] == "string":
                #     missing_value = "NaN"
                # var_context["missing_value"] = missing_value

                if "long_name" in variable["attributes"]:
                    var_context["long_name"] = variable["attributes"]["long_name"][
                        "data"
                    ]
                else:
                    var_context["long_name"] = name.capitalize()

                if "ioos_category" in variable["attributes"]:
                    var_context["ioos_category"] = variable["attributes"][
                        "ioos_category"
                    ]["data"]
                else:
                    var_context["ioos_category"] = "Unknown"

                if "units" in variable["attributes"]:
                    var_context["units"] = variable["attributes"]["units"]["data"]

                if "valid_min" in variable["attributes"]:
                    var_context["valid_min"] = variable["attributes"]["valid_min"][
                        "data"
                    ]

                if "valid_max" in variable["attributes"]:
                    var_context["valid_max"] = variable["attributes"]["valid_max"][
                        "data"
                    ]

                if "description" in variable["attributes"]:
                    var_context["description"] = variable["attributes"]["description"][
                        "data"
                    ]

                vars.append(var_template.render(variable=var_context))

            out = template.render(dataset=ds_context, variables=vars)
            # print(f"template: {out}")
            filename = ".".join([dataset_id, "xml"])
            configfile = os.path.join("/datasets.d", filename)
            # print(f"{dataset_id}: {filename}, {configfile}")
            with open(configfile, "w") as f:
                f.write(out)

            # # TODO: check if data dirs are there with example data
            # #       if not, build and add data using reg format
            # data_dir = os.path.join(
            #     "/data", "storage", "envds", "sensor", make, model, erddap_version
            # )
            # print(f"data_dir: {data_dir}")
            # os.makedirs(data_dir, exist_ok=True)
            # print(f"data_dir: done")

            return True
        except KeyError as e:
            self.logger.error("create_config_file", extra={"error": e})
            return False

    def check_config_file(self, basename) -> bool:
        filename = ".".join([basename, "xml"])
        configfile = os.path.join("/datasets.d", filename)
        # print(f"configfile: {configfile}, exists: {os.path.isfile(configfile)}")
        return os.path.isfile(configfile)

    async def create_init_datafile(
        self, source: str, erddap_version: str, message: Message
    ) -> bool:
        try:
            reg = self.data_registry[source][erddap_version]

            make = reg["attributes"]["make"]["data"]
            model = reg["attributes"]["model"]["data"]

            data_dir = os.path.join(
                "/data", "storage", "envds", "sensor", make, model, erddap_version
            )
            os.makedirs(data_dir, exist_ok=True)
            init_data_file = os.path.join(data_dir, "init_data.jsonl")
            # print(f"data_dir: {data_dir}")
            # result = glob.glob(init_data_search)
            # if result:
            #     return True
            # else:

            format = self.get_erddap_insert_sensor_format(
                data_source=source, erddap_version=erddap_version
            )
            # print(f"format: {format}")
            if not format:
                return False

            format["serial_number"] = message.data.data["attributes"]["serial_number"][
                "data"
            ]
            # print(f"format: {format}")

            # format = {
            #     "dataset_id": reg["dataset_id"],
            #     "make": reg["attributes"]["make"]["data"],
            #     "model": reg["attributes"]["model"]["data"],
            #     "version": reg["attributes"]["format_version"]["data"],
            #     "serial_number": "",
            #     "variables": {},
            # }

            header = []
            for key in format.keys():
                if key == "dataset_id":
                    pass
                elif key == "variables":
                    # print(f'variables: {format}, {format[key]}')
                    for variable in format["variables"].keys():
                        header.append(variable)
                else:
                    header.append(key)
            header.append("timestamp")
            header.append("author")
            header.append("command")

            _, init_params = await self.get_erddap_insert_sensor_data(message=message)
            data = []
            for key in header:
                try:
                    d = init_params[key]
                    print(f"d: {d}")
                    if isinstance(d, list):
                        data.append(f"[{','.join([str(x) for x in d])}]")
                        print(f"[{','.join([str(x) for x in d])}]")
                    elif type(d) != str:
                        data.append(str(d))
                    else:
                        data.append(d)
                    # data.append(init_params[key])
                except KeyError:
                    data.append("0")

            self.logger.debug("init_data", extra={"header": header, "data": data})
            # return True

            header_line = ",".join(header)

            # data_line = ",".join(data)
            # self.logger.debug("init_data_lines", extra={"header": header_line, "data": data})
            # TODO: Create init data file
            with open(init_data_file, "w") as f:
                f.write("[")
                f.write(",".join(header))
                f.write("]\n")
                # f.write(data)
                f.write("[")
                f.write(",".join(data))
                f.write("]\n")
                # f.writelines([header, data])
            self.logger.debug(
                "create_init_datafile - init file created",
                extra={"file": init_data_file},
            )
            return True

            # TODO: check if data dirs are there with example data
            #       if not, build and add data using reg format
            # data_dir = os.path.join(
            #     "/data", "storage", "envds", "sensor", make, model, erddap_version
            # )
            # print(f"data_dir: {data_dir}")
            # os.makedirs(data_dir, exist_ok=True)
            # print(f"data_dir: done")

        except KeyError as e:
            self.logger.error("create_init_datafile", extra={"error": e})
            return False

    def check_init_datafile(self, make: str, model: str, erddap_version: str) -> bool:

        data_dir = os.path.join(
            "/data", "storage", "envds", "sensor", make, model, erddap_version
        )
        init_data_search = os.path.join(data_dir, "init_data.jsonl")

        # result = glob.glob(init_data_search)
        result = os.path.isfile(init_data_search)
        # print(f"init_data_file: {init_data_search}, exists: {os.path.isfile(result)}")
        return result

    async def check_registration_loop(self):

        while True:
            try:
                message = await self.registry_buffer.get()

                if message:

                    try:
                        atts = message.data.data["attributes"]
                        variables = message.data.data["variables"]

                        erddap_version = (
                            f'v{atts["format_version"]["data"].split(".")[0]}'
                        )
                        source = message.data["source"]
                        make = atts["make"]["data"]
                        model = atts["model"]["data"]
                        version = atts["format_version"]["data"]
                        dataset_id = f"{make}_{model}_{erddap_version}"
                        self.logger.debug("check_registration_loop", extra={"dataset_id": dataset_id})
                        params = {
                            "make": make,
                            "model": model,
                            # 'serial_number': atts["serial_number"],
                            "version": version,
                        }
                        # print(f"params: {params}")

                        reg = await get_sensor_type_registration(**params)
                        self.logger.debug("check_registration_loop", extra={"reg": reg})
                        if reg:
                            self.logger.debug(
                                "register_sensor_loop", extra={"reg": reg.dict()}
                            )

                            if source not in self.data_registry:
                                self.data_registry[source] = {
                                    erddap_version: {
                                        "dataset_id": dataset_id,
                                        "attributes": reg.metadata["attributes"],
                                        "variables": reg.metadata["variables"],
                                    }
                                }
                            elif reg.version not in self.data_registry[source]:
                                self.data_registry[source][erddap_version] = {
                                    "dataset_id": dataset_id,
                                    "attributes": reg.metadata["attributes"],
                                    "variables": reg.metadata["variables"],
                                }

                        else:

                            pass
                            # put message in holding pattern - check again in 5? seconds and keep track
                            #   of how many times it is checked. After N attempts, dump it
                            await self.holding_buffer.put((get_datetime(), message))
                            continue

                        # make sure config file has been created
                        if not self.check_config_file(dataset_id):  # and
                            # print(f"reg.metadata: {reg.dict()}")
                            if not await self.create_config_file(
                                dataset_id,
                                metadata=reg.metadata,
                                # attributes=atts,
                                # variables=variables
                            ):
                                await self.holding_buffer.put(message)
                                continue

                        # check to make sure initial data file on dataserver
                        if not self.check_init_datafile(
                            make=make, model=model, erddap_version=erddap_version
                        ):
                            if not await self.create_init_datafile(
                                source, erddap_version, message
                            ):
                                await self.holding_buffer.put(message)
                                continue

                        # if all satisfied, pass along to be inserted into dataserver
                        await self.insert_buffer.put(message)

                    except KeyError as e:
                        self.logger.error("check_registration_loop", extra={"error": e})
                        pass

            except Exception as e:
                self.logger.error("check_registration_loop", extra={"error": e})
                await asyncio.sleep(1)

        # get registry from db and add to local registry
        # check if erddap has config for data
        #   if not, create config file and dir structure if needed

        # pass data to insert or buffer until erddap is ready?

    def get_erddap_insert_sensor_format(
        self, data_source: str, erddap_version: str
    ) -> dict:

        try:
            # print(f"data_registry: {self.data_registry}")
            # print(data_source, erddap_version)
            reg = self.data_registry[data_source][erddap_version]
            # print(reg)
            format = {
                "dataset_id": reg["dataset_id"],
                "make": reg["attributes"]["make"]["data"],
                "model": reg["attributes"]["model"]["data"],
                "version": reg["attributes"]["format_version"]["data"],
                "serial_number": "",
                "variables": {},
            }
            # print(f"current format: {format}")

            for name, variable in reg["variables"].items():
                format["variables"][name] = {"shape": variable["shape"]}

            return format

        except KeyError:
            return None

    async def get_erddap_insert_sensor_data(
        self, message: Message, author: str = "default"
    ) -> Tuple[str, dict]:

        try:
            source = message.data["source"]
            data = message.data.data
            version = data["attributes"]["format_version"]["data"]
            erddap_version = f'v{version.split(".")[0]}'
            serial_number = data["attributes"]["serial_number"]["data"]

            format = self.get_erddap_insert_sensor_format(
                data_source=source, erddap_version=erddap_version
            )
            if format:
                out = {
                    "make": format["make"],
                    "model": format["model"],
                    "version": format["version"],
                    "serial_number": serial_number,
                }
                # return "abc", {}
                for name, variable in format["variables"].items():
                    if name == "time":
                        if name not in data["variables"]:
                            return None
                        out[name] = data["variables"][name]["data"]
                    else:
                        shape = len(format["variables"][name]["shape"])

                        if shape > 1:
                            if shape == 2:
                                if name not in data["variables"]:
                                    values = [""]
                                else:
                                    values = data["variables"][name]["data"]
                                out[name] = f'[{",".join([str(x) for x in values])}]'
                            elif shape == 3:
                                # TODO: figure out comprehension for this
                                pass
                        else:
                            if name not in data["variables"]:
                                value = ""
                            else:
                                value = data["variables"][name]["data"]
                            out[name] = value

                out["author"] = author
                return format["dataset_id"], out

        except Exception as e:
            self.logger.error("get_erddap_insert_sensor_data error", extra={"error": e})
            pass

        return None, None

    async def erddap_insert_loop(self):

        while True:
            try:
                message = await self.insert_buffer.get()
                if message:
                    source = message.data["source"]
                    # author = "super_secret_author"

                    # parts = source.split(".")
                    # sensor_name = parts[-1].split(Sensor.ID_DELIM)

                    # self.logger.debug(
                    #     "dataserver.handle_data",
                    #     extra={
                    #         "sensor": parts[-1].split(Sensor.ID_DELIM),
                    #         "data": message.data.data,
                    #     },
                    # )
                    # try:
                    #     atts = message.data.data["attributes"]
                    #     variables = message.data.data["variables"]

                    #     # print(
                    #     #     f"get data format from meta_registry if not in local reg: {atts['make']}, {atts['model']}, {atts['serial_number']}"
                    #     # )

                    #     version = atts["format_version"]["data"]
                    #     # erddap version format: v<major version>, e.g., v1
                    #     erddap_version = f'v{version.split(".")[0]}'
                    #     # source = message.data["source"]
                    #     make = atts["make"]["data"]
                    #     model = atts["model"]["data"]

                    #     dataset_id = f"{make}_{model}_{erddap_version}"

                    #     try:
                    #         reg = self.data_registry[source][erddap_version]
                    #     except KeyError:
                    #         self.logger.warn(
                    #             "dataserver - data not registered",
                    #             extra={"source": source, "version": version},
                    #         )
                    #         await self.holding_buffer.put((get_datetime(), message))
                    #         continue

                    #     # TODO: check subversions and replace config if necessary
                    #     params = {
                    #         "make": make,
                    #         "model": model,
                    #         "version": version,
                    #         "serial_number": atts["serial_number"]["data"],
                    #     }

                    #     for name, variable in variables.items():
                    #         params[name] = variable["data"]

                    #     author = "super_secret_author"
                    #     params["author"] = author
                    # except KeyError:
                    #     pass

                    # TODO: find better way to set author
                    author = "super_secret_author"
                    hardcode_url = "https://erddap.envds:8443/erddap/tabledap"
                    # erddap_dataset = f"{params['make']}_{params['model']}"
                    # dataset_id = f"{make}_{model}_{erddap_version}"
                    # url = f"{hardcode_url}/{dataset_id}.insert"

                    # TODO: make sure local reg is using full metadata (type, shape, etc)
                    dataset_id, params = await self.get_erddap_insert_sensor_data(
                        message=message, author=author
                    )
                    if dataset_id is None or params is None:
                        self.logger.warn(
                            "dataserver - data not registered",
                            extra={"source": source},
                        )
                        await self.holding_buffer.put((get_datetime(), message))
                        continue

                    self.logger.debug(
                        "insert data", extra={"id": dataset_id, "params": params}
                    )
                    url = f"{hardcode_url}/{dataset_id}.insert"
                    # params = params
                    try:
                        # self.logger.debug("POST", extra={"url": url, "params": params})
                        r = httpx.post(url, params=params, verify=False)
                        self.logger.info(f"Sent POST to ERRDAP @ {r.url}", extra=params)
                        r.raise_for_status()
                        # return r.json()
                    except httpx.HTTPError as e:
                        self.logger.error(str(e))
                        await self.holding_buffer.put((get_datetime(), message))
                        # return str(e)
                else:
                    await asyncio.sleep(0.1)
            except Exception as e:
                self.logger.error("data_loop", extra={"error": e})
                await asyncio.sleep(1)

    def run(self):
        super(envdsDataserver, self).run()

        self.enable()


class ServerConfig(BaseModel):
    host: str = "localhost"
    port: int = 9080
    log_level: str = "info"


async def test_task():
    while True:
        await asyncio.sleep(1)
        # print("daq test_task...")
        logger = logging.getLogger("envds.info")
        logger.info("test_task", extra={"test": "daq task"})


async def shutdown():
    print("shutting down")
    for task in task_list:
        print(f"cancel: {task}")
        task.cancel()


async def main(server_config: ServerConfig = None):
    # uiconfig = UIConfig(**config)
    if server_config is None:
        server_config = ServerConfig()
    print(server_config)

    print("starting daq test task")

    envdsLogger(level=logging.DEBUG).init_logger()
    logger = logging.getLogger("envds-files")

    print("main:1")
    ds = envdsDataserver()
    print("main:2")
    ds.run()
    print("main:3")
    # await asyncio.sleep(2)
    # files.enable()
    # task_list.append(asyncio.create_task(files.run()))
    # await asyncio.sleep(2)

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))

    # # print(LOGGING_CONFIG)
    # dict_config = {
    #     "version": 1,
    #     "disable_existing_loggers": False,
    #     "formatters": {
    #         "logfmt": {
    #             "()": "logfmter.Logfmter",
    #             "keys": ["at", "when", "name"],
    #             "mapping": {"at": "levelname", "when": "asctime"},
    #             "datefmt": get_datetime_format(),
    #         },
    #         "access": {
    #             "()": "uvicorn.logging.AccessFormatter",
    #             "fmt": '%(levelprefix)s %(asctime)s :: %(client_addr)s - "%(request_line)s" %(status_code)s',
    #             "use_colors": True,
    #         },
    #     },
    #     "handlers": {
    #         "console": {"class": "logging.StreamHandler", "formatter": "logfmt"},
    #         "access": {
    #             "formatter": "access",
    #             "class": "logging.StreamHandler",
    #             "stream": "ext://sys.stdout",
    #         },
    #     },
    #     "loggers": {
    #         "": {"handlers": ["console"], "level": "INFO"},
    #         "uvicorn.access": {
    #             "handlers": ["access"],
    #             "level": "INFO",
    #             "propagate": False,
    #         },
    #     },
    # }
    # logging.config.dictConfig(dict_config)

    # envdsLogger().init_logger()
    # logger = logging.getLogger("envds-daq")

    # test = envdsBase()
    # task_list.append(asyncio.create_task(test_task()))
    # logger.debug("starting envdsFiles")

    config = uvicorn.Config(
        "main:app",
        host=server_config.host,
        port=server_config.port,
        log_level=server_config.log_level,
        root_path="/envds/dataserver",
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    await server.serve()

    print("starting shutdown...")
    await shutdown()
    print("done.")


if __name__ == "__main__":

    BASE_DIR = os.path.dirname(
        # os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.path.dirname(os.path.abspath(__file__))
    )
    # insert BASE at beginning of paths
    sys.path.insert(0, BASE_DIR)
    print(sys.path, BASE_DIR)

    print(sys.argv)
    config = ServerConfig()
    try:
        index = sys.argv.index("--host")
        host = sys.argv[index + 1]
        config.host = host
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--port")
        port = sys.argv[index + 1]
        config.port = int(port)
    except (ValueError, IndexError):
        pass

    try:
        index = sys.argv.index("--log_level")
        ll = sys.argv[index + 1]
        config.log_level = ll
    except (ValueError, IndexError):
        pass

    # print(LOGGING_CONFIG)

    # handler = logging.StreamHandler(sys.stdout)
    # formatter = Logfmter(
    #     keys=["at", "when", "name"],
    #     mapping={"at": "levelname", "when": "asctime"},
    #     datefmt=get_datetime_format()
    # )

    # # # self.logger = envdsLogger().get_logger(self.__class__.__name__)
    # # handler.setFormatter(formatter)
    # # # logging.basicConfig(handlers=[handler])
    # root_logger = logging.getLogger(__name__)
    # # # root_logger = logging.getLogger(self.__class__.__name__)
    # # # root_logger.addHandler(handler)
    # root_logger.addHandler(handler)
    # root_logger.setLevel(logging.INFO) # this should be settable
    # root_logger.info("in run", extra={"test": "value"})
    # print(root_logger.__dict__)

    # if "--host" in sys.argv:
    #     print(sys.argv.index("--host"))
    #     print(sys)
    asyncio.run(main(config))
