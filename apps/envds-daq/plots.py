import asyncio
from datetime import datetime, timedelta
import json
from socket import socket
import panel as pn
from panel.theme import Material, Native

import pandas as pd
import numpy as np
import holoviews as hv
import xarray as xr
from streamz import Stream
import hvplot.xarray
from holoviews.streams import Pipe
from bokeh.models import DatetimeTickFormatter
from bokeh.settings import settings

from bokeh.embed import server_document
from envds.daq.db import (
    get_sensor_type_registration,
    get_sensor_registration,
    get_sensor_type_metadata,
)

from envds.util.util import (
    # get_datetime_format,
    # time_to_next,
    # get_datetime,
    # get_datetime_string,
    # datetime_to_string,
    string_to_datetime,
)


class PlotDataManager(object):
    """docstring for PlotManager."""

    data_map = {"sensor": {}}

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(PlotDataManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        super().__init__()

        print("init")

    def get(self, type: str, **kwargs):
        if type == "sensor":
            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                print(f"not enough info to get sensor")
                return None
            print(f"PlotDataManager data_map: {self.data_map}")
            try:
                data = self.data_map[type][make][model][serial_number]
                # print(f"PlotManager app: {app.get_server_url()}")
            except KeyError:
                data = self._create(
                    type, make=make, model=model, serial_number=serial_number
                )
                self.data_map[type][make][model][serial_number] = data
        # print(f"PlotManager.get: app={app} - {make}, {model}, {serial_number}")
        return data

    def _create(self, type: str, **kwargs):

        if type == "sensor":

            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                return None

            try:
                print(f"_create: {type}, {make}, {model}, {serial_number}")
                data = SensorPlotData(
                    make=make,
                    model=model,
                    serial_number=serial_number,
                )
                print(f"_create: {type}, {make}, {model}, {serial_number}, {data}")
                if make not in self.data_map[type]:
                    self.data_map[type][make] = dict()
                if model not in self.data_map[type][make]:
                    self.data_map[type][make][model] = dict()
                self.data_map[type][make][model][serial_number] = data
                # print(f"app_map: {self.app_map}")
                return data
            except KeyError:
                return None

        return None


class PlotData(object):
    """docstring for PlotApp."""

    def __init__(self):
        super(PlotData, self).__init__()

        # self.server = None
        # self.port = None
        # self.url = ""

        self.pipe = None
        self.source = None

        # self.app = None

        self.data_tmpl = dict()
        # self.plot_map = None

        self.buffer_size = 120  # in minutes

    def cat_ds(self, current, new_data):
        # print(f"concat: current = {current}")
        # print(f"concat: new_data = {new_data}")
        # new_ds = self.ds_from_tmpl(new_data)
        current = xr.concat([current, new_data], dim="time")
        # print(f"concat: current (again) = {current}")

        curr_time = datetime.utcnow()
        past_time = curr_time - timedelta(minutes=120)
        np.datetime64(past_time)
        current = current.sel(time=(current.time > np.datetime64(past_time)), drop=True)
        # print(current.time)
        # print(f"concat: current(again again) {current}")
        return current

    async def update(self, new_data):
        pass


class SensorPlotData(PlotData):
    """docstring for SensorPlotData."""

    def __init__(self, make: str, model: str, serial_number: str):
        super(SensorPlotData, self).__init__()

        self.make = make
        self.model = model
        self.serial_number = serial_number
        # self.url = "/".join(["", "sensor", self.make, self.model, self.serial_number])

        # self.data_tmpl = dict()

        print("SensorPlotData init finished")

    async def _create(self, data):
        print("_create SensorPlotData")
        meta = await get_sensor_type_metadata(self.make, self.model)
        # reg = await get_sensor_registration(self.make, self.model, self.serial_number)
        # print(f"meta: {meta}")
        # build data template
        print(f"meta: {meta}")
        # scan for 2d data
        coord_names = ["time"]
        vars_1d_names = []
        vars_2d_names = []
        for name, variable in meta["variables"].items():
            # print(f"type: {variable['type']}, {variable['type'] not in ['float', 'int']}")
            if variable["type"] not in ["float", "int"]:  # skip non numeric variables
                continue

            # print(f"shape: {variable['shape']}")
            if len(variable["shape"]) > 1:
                for d in variable["shape"]:
                    if d not in coord_names:
                        coord_names.append(d)
                if name not in coord_names and name not in vars_2d_names:
                    vars_2d_names.append(name)
            else:
                if name not in coord_names and name not in vars_1d_names:
                    vars_1d_names.append(name)
                    print(f"vars_1d: {name}, {vars_1d_names}")

        # print(f"coords: {coord_names}, vars_1d: {vars_1d_names}")

        self.data_tmpl = {
            "coords": {},
            "attrs": {},
            "dims": {},
            "data_vars": {},
        }
        print(f"data_tmpl: {self.data_tmpl}")
        for name in coord_names:
            # print(f"start tmpl: {name}, {data}")
            if name in data["variables"]:
                attrs = {}
                if "attributes" in meta["variables"][name]:
                    for attname, attval in meta["variables"][name][
                        "attributes"
                    ].items():
                        print(f"{attname}, {attval}")
                        attrs[attname] = attval["data"]
                # val = [data["variables"][name]["data"]]

                if name == "time":
                    val = string_to_datetime(data["variables"][name]["data"])
                else:
                    val = data["variables"][name]["data"]

                if not isinstance(val, list):
                    val = [val]

                # if isinstance(data["variables"][name]["data"], list):
                #     val = data["variables"][name]["data"]
                self.data_tmpl["coords"][name] = {
                    "dims": (name,),
                    "attrs": attrs,
                    "data": val,
                }
                self.data_tmpl["dims"][name] = len(val)

                # print(f"dims1: {self.data_tmpl['dims']}")
                if name not in self.data_tmpl["dims"]:
                    self.data_tmpl["dims"][name] = 0
                    # print(f"dims2: {self.data_tmpl['dims']}")
                self.data_tmpl["dims"][name] = len(val)
                # print(f"dims3: {self.data_tmpl['dims']}")
        # print(f"data_tmpl: {self.data_tmpl}")
        for name in vars_1d_names:
            if name in data["variables"]:
                attrs = {}
                if "attributes" in meta["variables"][name]:
                    for attname, attval in meta["variables"][name][
                        "attributes"
                    ].items():
                        attrs[attname] = attval["data"]
                # if "attributes" in meta["variables"][name]:
                #     attrs = meta["variables"][name]["attributes"]
                if name == "time":
                    data_val = string_to_datetime(data["variables"][name]["data"])
                else:
                    data_val = data["variables"][name]["data"]
                self.data_tmpl["data_vars"][name] = {
                    "dims": ("time",),
                    "attrs": attrs,
                    "data": [data_val],
                }

        # print(f"data_tmpl: {self.data_tmpl}")
        for name in vars_2d_names:
            attrs = {}
            if "attributes" in meta["variables"][name]:
                for attname, attval in meta["variables"][name]["attributes"].items():
                    attrs[attname] = attval["data"]
            # if "attributes" in meta["variables"][name]:
            #     attrs = meta["variables"][name]["attributes"]

            dims = tuple()
            for d in meta["variables"][name]["shape"]:
                dims += (d,)
            self.data_tmpl["data_vars"][name] = {
                "dims": dims,
                "attrs": attrs,
                "data": [data["variables"][name]["data"]],
            }

        ds = xr.Dataset.from_dict(self.data_tmpl)
        # print(f"ds: {ds}")
        self.pipe = Pipe(data=ds)
        # print(f"pipe: {self.pipe}")

        self.source = Stream()
        self.source.accumulate(self.cat_ds).sink(self.pipe.send)

        # self.source.accumulate(cat_ds2).sink(self.pipe.send)
        # print("_create: data type = {type(ds)}")
        # self.source.emit(ds)
        print(f"_create: pipe.data =  {self.pipe.data}")

    def get_var_list(self):  # , shape=[], exclude_time=False):
        current_ds = self.pipe.data
        clist = list(current_ds.coords.keys())
        vlist = list(current_ds.variables.keys())
        for c in clist:
            if c in vlist:
                vlist.remove(c)
        #     if c != "time" and c in vlist:
        #         vlist.remove(c)
        # if exclude_time and "time" in vlist:
        #     vlist.remove("time")

        # if shape != []:
        #     mod_vlist = []
        #     for v in vlist:
        #         if list(current_ds[v].coords.keys()) == shape:
        #             mod_vlist.append(v)
        #     return mod_vlist
        return clist, vlist

    async def update(self, new_data):
        await super().update(new_data)

        # print(f"new_data: {new_data}")
        # check if first data
        if self.pipe is None:
            await self._create(new_data)
            # new_ds = self.ds_from_tmpl(new_data)
            # print(f"update(current): {type(self.pipe.data)}, {self.pipe.data}")
            # print(f"update: data type = {type(new_ds)}, {new_ds}")
            # self.source.emit(new_ds)
            # print(f"update: pipe.data =  {self.pipe.data['time'].size}")

            return

        # if self.pipe and self.pipe.data is None:

        # # print(f"pipe.data: {self.pipe.data['time']}")
        # if self.pipe.data["time"].size < 2:
        #     new_ds = self.ds_from_tmpl(new_data)
        #     # print(f"update(new_ds): {new_ds}, {type(new_ds)}")
        #     if new_ds:
        #         # print(f"update(current): {self.pipe.data}, {type(self.pipe.data)}")
        #         # print(f"update(new_ds): {new_ds}, {type(new_ds)}")
        #         self.source.emit(new_ds)
        #         # print(f"update(current) after: {self.pipe.data}")
        #         # print(f"update(new_ds) after: {new_ds}")
        #         # create plot object
        #         self.app = self.create_plots()
        #         # print(f"done creating plots")
        #         self.create_server()
        #         # print(f"done creating server")
        #         return

        new_ds = self.ds_from_tmpl(new_data)
        if new_ds:
            self.source.emit(new_ds)
            # if self.pipe.data["time"].size >= 2 and self.server is None:
            #     # self.app = self.create_plots()
            #     self.create_server()

    def ds_from_tmpl(self, new_data):
        # current_ds = self.pipe.data
        # clist = list(current_ds.coords.keys())
        # vlist = list(current_ds.variables.keys())
        # for c in clist:
        #     if c != "time" and c in vlist:
        #         vlist.remove(c)
        clist, vlist = self.get_var_list()
        # print(f"vlist: {vlist}")
        # print(f"update:data_tmpl: {self.data_tmpl['dims']}, {self.data_tmpl}")
        try:
            for c in clist:
                # print(f"ds_from_tmpl: {c}")
                if c == "time":
                    # print(new_data["variables"][c]["data"])
                    data_val = string_to_datetime(new_data["variables"][c]["data"])
                    # print(data_val)
                else:
                    data_val = new_data["variables"][c]["data"]
                # print(f"ds_from_tmpl: {data_val}")

                if not isinstance(data_val, list):
                    data_val = [data_val]

                # print(f"ds_from_tmpl-coords1: {self.data_tmpl['coords']}")
                self.data_tmpl["coords"][c]["data"] = data_val
                # print(f"ds_from_tmpl-coords2: {self.data_tmpl['coords']}")

            for v in vlist:
                # print(f"ds_from_tmpl: {v}")
                if v == "time":
                    # print(new_data["variables"][v]["data"])
                    data_val = string_to_datetime(new_data["variables"][v]["data"])
                    # print(data_val)
                else:
                    data_val = new_data["variables"][v]["data"]
                if not isinstance(data_val, list):
                    data_val = [data_val]

                # print(f"ds_from_tmpl: {data_val}")
                self.data_tmpl["data_vars"][v]["data"] = data_val

            # print(f"{self.data_tmpl.keys()}, {self.data_tmpl['dims']}")
            # print(f"{self.data_tmpl}")
            new_ds = xr.Dataset.from_dict(self.data_tmpl)
            # print(f"ds_from_tmpl: {new_ds}")
            return new_ds
        except (KeyError, ValueError) as e:
            print(f"ds_from_tmpl error: {e}")
            return None


class PlotManager(object):
    """docstring for PlotManager."""

    app_map = {"sensor": {}}
    server_map = {"sensor": {}}
    port_map = {}

    def __new__(cls):
        if not hasattr(cls, "instance"):
            cls.instance = super(PlotManager, cls).__new__(cls)
        return cls.instance

    def __init__(self):
        super().__init__()

        print("init")

    def get(self, type: str, **kwargs):
        if type == "sensor":
            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                print(f"not enough info to get sensor")
                return None
            # print(f"PlotManager app_map: {self.app_map}")
            try:
                app = self.app_map[type][make][model][serial_number]
                # print(f"PlotManager app: {app.get_server_url()}")
            except KeyError:
                app = self._create(
                    type, make=make, model=model, serial_number=serial_number
                )
                self.app_map[type][make][model][serial_number] = app
        # print(f"PlotManager.get: app={app} - {make}, {model}, {serial_number}")
        return app

    def get_server(self, type: str, **kwargs):
        if type == "sensor":
            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                print(f"not enough info to get sensor")
                return None
            # print(f"PlotManager app_map: {self.app_map}")
            try:
                # app = self.app_map[type][make][model][serial_number]

                server = self.server_map[type][make][model][serial_number]
                # print(f"PlotManager app: {app.get_server_url()}")
            except KeyError:

                server = self._create(
                    type, make=make, model=model, serial_number=serial_number
                )
                # self.server_map[type][make][model][serial_number] = server
        print(f"server_map: {self.server_map}")
        # print(f"PlotManager.get: app={app} - {make}, {model}, {serial_number}")
        return server

    def _create(self, type: str, **kwargs):

        if type == "sensor":

            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                return None

            try:
                data = PlotDataManager().get(
                    type="sensor", make=make, model=model, serial_number=serial_number
                )
                if data is None:
                    return None

                data_pipe = data.pipe
                # Don't create the server until there is enough data to create a plot
                if "time" not in data_pipe.data or data_pipe.data["time"].size < 2:
                    return None

                url = "/".join([type, make, model, serial_number])

                settings.resources = "inline"

                # get free port
                port = 0
                for p in range(5000,5021):
                    if p in self.port_map:
                        continue
                    else:
                        port = p
                        break

                # TODO allow host to be passed as arg or env variable

                # port = 5004
                if port >= 5000 and port <=5020:
                    server = pn.serve(
                        # {self.url: self.app.servable()},
                        {
                            url: SensorPlotApp(
                                data_pipe=data_pipe,
                                make=make,
                                model=model,
                                serial_number=serial_number,
                            )
                            .create_plots()
                            # .servable()
                        },
                        # {key: self.app.servable()},
                        port=port,
                        allow_websocket_origin=["*"],
                        address="0.0.0.0",
                        prefix=f"/plots/envds/daq/{port}",
                        host="127.0.0.1:8080",
                        show=False,
                        log_level="debug",
                    )

                    self.port_map[port] = server

                    # app = SensorPlotApp(
                    #     make=make,
                    #     model=model,
                    #     serial_number=serial_number,
                    # )
                    # print(f"_create: {type}, {make}, {model}, {serial_number}, {app}")
                    if make not in self.server_map[type]:
                        self.server_map[type][make] = dict()
                    if model not in self.server_map[type][make]:
                        self.server_map[type][make][model] = dict()
                    self.server_map[type][make][model][serial_number] = server
                    # print(f"app_map: {self.app_map}")
                    return server
            except KeyError:
                return None

        return None

    # async def update(self, type, data, **kwargs):

    #     app = self.get(type=type, **kwargs)
    #     if app:
    #         await app.update(data)

    def get_server_document(self, type, **kwargs):

        # app = self.get(type=type, **kwargs)

        # if plot server is None
        # instantiate PlotApp using PlotData
        # create plot server

        if type == "sensor":

            try:
                make = kwargs["make"]
                model = kwargs["model"]
                serial_number = kwargs["serial_number"]
            except KeyError:
                return ""

            server = self.get_server(type, **kwargs)
            if server:
                prefix = server.prefix
                url = "/".join([prefix, type, make, model, serial_number])
                print(f"get_server_documents:url = {url}")
                return server_document(url=url, relative_urls=True)

        # if app:
        #     url = app.get_server_url()
        #     # url = self.url
        #     # url = "/plots/test"
        #     if url:
        #         return server_document(url=url, relative_urls=True)
        #         # return server_document(relative_urls=True)
        return ""


class PlotApp(object):
    """docstring for PlotApp."""

    def __init__(self):
        super(PlotApp, self).__init__()

        self.server = None
        self.port = None
        self.url = ""

        self.pipe = None
        self.source = None

        self.app = None

        self.data_tmpl = dict()
        self.plot_map = None

        self.buffer_size = 120  # in minutes

    def create_app(self):
        return pn.Card()

    def get_server_url(self):
        # return f"http://127.0.0.1:{self.port}{self.url}"
        # return f"http://0.0.0.0:{self.port}/plots/envds/sensor{self.url}"
        # return f"http://localhost:8090/plots/envds/daq/5004{self.url}"
        # return f"http://localhost:8090/plots/envds/sensor{self.url}"
        # return f"http://localhost:8090/plots/test"
        return f"/plots/envds/daq/5004{self.url}"
        # return self.url

    def get_dt_formatter(self):
        dt_formatter = DatetimeTickFormatter(
            years="%Y",
            months="%Y-%m",
            days="%F",
            hours="%m-%d %H:%M",
            hourmin="%m-%d %H:%M",
            minutes="%H:%M",
            minsec="%T",
            seconds="%T",
            milliseconds="%T.%1N",
        )
        return dt_formatter

    def cat_ds(self, current, new_data):
        # print(f"concat: current = {current}")
        # print(f"concat: new_data = {new_data}")
        # new_ds = self.ds_from_tmpl(new_data)
        current = xr.concat([current, new_data], dim="time")
        # print(f"concat: current (again) = {current}")

        curr_time = datetime.utcnow()
        past_time = curr_time - timedelta(minutes=120)
        np.datetime64(past_time)
        current = current.sel(time=(current.time > np.datetime64(past_time)), drop=True)
        # print(current.time)
        # print(f"concat: current(again again) {current}")
        return current

    async def update(self, new_data):
        pass

    def create_server(self):
        # if self.app is None:
        #     self.server = None
        #     return

        # # get port
        # self.port = 0
        # with socket() as s:
        #     s.bind(('',0))
        #     self.port = s.getsockname()[1]
        # self.port = 5000

        # if self.port > 0:
        #     print(f"create_server: {self.url}, {self.app.servable()}")

        #     self.server = pn.serve(
        #         {self.url: self.app.servable()},
        #         port=self.port,
        #         allow_websocket_origin=["*"],
        #         address="0.0.0.0",
        #         # prefix="/plots/envds/daq",
        #         # host="127.0.0.1:8090",
        #         show=False
        #     )

        print(f"*** creating server!")
        self.port = 5004
        key = "/".join(["", "plots", "envds", "daq", f"{self.port}"]) + self.url

        settings.resources = "inline"

        self.server = pn.serve(
            # {self.url: self.app.servable()},
            {self.url: self.create_app().servable()},
            # {key: self.app.servable()},
            port=self.port,
            allow_websocket_origin=["*"],
            address="0.0.0.0",
            prefix="/plots/envds/daq/5004",
            host="127.0.0.1:8090",
            show=False,
            log_level="debug",
        )


class SensorPlotApp(PlotApp):
    """docstring for SensorPlotApp."""

    def __init__(self, data_pipe: Pipe, make: str, model: str, serial_number: str):
        super(SensorPlotApp, self).__init__()

        self.pipe = data_pipe
        self.make = make
        self.model = model
        self.serial_number = serial_number
        self.url = "/".join(["", "sensor", self.make, self.model, self.serial_number])

        # self.data_tmpl = dict()

        print("SensorPlotApp init finished")

    async def _create(self, data):

        meta = await get_sensor_type_metadata(self.make, self.model)
        # reg = await get_sensor_registration(self.make, self.model, self.serial_number)
        # print(f"meta: {meta}")
        # build data template

        # scan for 2d data
        coord_names = ["time"]
        vars_1d_names = []
        vars_2d_names = []
        for name, variable in meta["variables"].items():
            # print(f"type: {variable['type']}, {variable['type'] not in ['float', 'int']}")
            if variable["type"] not in ["float", "int"]:  # skip non numeric variables
                continue

            # print(f"shape: {variable['shape']}")
            if len(variable["shape"]) > 1:
                for d in variable["shape"]:
                    if d not in coord_names:
                        coord_names.append(d)
                if name not in coord_names and name not in vars_2d_names:
                    vars_2d_names.append(name)
            else:
                if name not in coord_names and name not in vars_1d_names:
                    vars_1d_names.append(name)
                    print(f"vars_1d: {name}, {vars_1d_names}")

        # print(f"coords: {coord_names}, vars_1d: {vars_1d_names}")

        self.data_tmpl = {
            "coords": {},
            "attrs": {},
            "dims": {},
            "data_vars": {},
        }

        for name in coord_names:
            # print(f"start tmpl: {name}, {data}")
            if name in data["variables"]:
                attrs = {}
                if "attributes" in meta["variables"][name]:
                    for attname, attval in meta["variables"][name][
                        "attributes"
                    ].items():
                        print(f"{attname}, {attval}")
                        attrs[attname] = attval["data"]
                # val = [data["variables"][name]["data"]]

                if name == "time":
                    val = string_to_datetime(data["variables"][name]["data"])
                else:
                    val = data["variables"][name]["data"]

                if not isinstance(val, list):
                    val = [val]

                # if isinstance(data["variables"][name]["data"], list):
                #     val = data["variables"][name]["data"]
                self.data_tmpl["coords"][name] = {
                    "dims": (name,),
                    "attrs": attrs,
                    "data": val,
                }
                self.data_tmpl["dims"][name] = len(val)

                # print(f"dims1: {self.data_tmpl['dims']}")
                if name not in self.data_tmpl["dims"]:
                    self.data_tmpl["dims"][name] = 0
                    # print(f"dims2: {self.data_tmpl['dims']}")
                self.data_tmpl["dims"][name] = len(val)
                # print(f"dims3: {self.data_tmpl['dims']}")
        # print(f"data_tmpl: {self.data_tmpl}")
        for name in vars_1d_names:
            if name in data["variables"]:
                attrs = {}
                if "attributes" in meta["variables"][name]:
                    for attname, attval in meta["variables"][name][
                        "attributes"
                    ].items():
                        attrs[attname] = attval["data"]
                # if "attributes" in meta["variables"][name]:
                #     attrs = meta["variables"][name]["attributes"]
                if name == "time":
                    data_val = string_to_datetime(data["variables"][name]["data"])
                else:
                    data_val = data["variables"][name]["data"]
                self.data_tmpl["data_vars"][name] = {
                    "dims": ("time",),
                    "attrs": attrs,
                    "data": [data_val],
                }

        # print(f"data_tmpl: {self.data_tmpl}")
        for name in vars_2d_names:
            attrs = {}
            if "attributes" in meta["variables"][name]:
                for attname, attval in meta["variables"][name]["attributes"].items():
                    attrs[attname] = attval["data"]
            # if "attributes" in meta["variables"][name]:
            #     attrs = meta["variables"][name]["attributes"]

            dims = tuple()
            for d in meta["variables"][name]["shape"]:
                dims += (d,)
            self.data_tmpl["data_vars"][name] = {
                "dims": dims,
                "attrs": attrs,
                "data": [data["variables"][name]["data"]],
            }

        ds = xr.Dataset.from_dict(self.data_tmpl)
        # print(f"ds: {ds}")
        self.pipe = Pipe(data=ds)
        # print(f"pipe: {self.pipe}")
        self.source = Stream()
        self.source.accumulate(self.cat_ds).sink(self.pipe.send)
        # self.source.accumulate(cat_ds2).sink(self.pipe.send)
        # print("_create: data type = {type(ds)}")
        # self.source.emit(ds)
        # print(f"_create: pipe.data =  {self.pipe.data}")

    def get_var_list(self):  # , shape=[], exclude_time=False):
        current_ds = self.pipe.data
        clist = list(current_ds.coords.keys())
        vlist = list(current_ds.variables.keys())
        for c in clist:
            if c in vlist:
                vlist.remove(c)
        #     if c != "time" and c in vlist:
        #         vlist.remove(c)
        # if exclude_time and "time" in vlist:
        #     vlist.remove("time")

        # if shape != []:
        #     mod_vlist = []
        #     for v in vlist:
        #         if list(current_ds[v].coords.keys()) == shape:
        #             mod_vlist.append(v)
        #     return mod_vlist
        return clist, vlist

    async def update(self, new_data):
        await super().update(new_data)

        # print(f"new_data: {new_data}")
        # check if first data
        if self.pipe is None:
            await self._create(new_data)
            # new_ds = self.ds_from_tmpl(new_data)
            # print(f"update(current): {type(self.pipe.data)}, {self.pipe.data}")
            # print(f"update: data type = {type(new_ds)}, {new_ds}")
            # self.source.emit(new_ds)
            # print(f"update: pipe.data =  {self.pipe.data['time'].size}")

            return

        # if self.pipe and self.pipe.data is None:

        # # print(f"pipe.data: {self.pipe.data['time']}")
        # if self.pipe.data["time"].size < 2:
        #     new_ds = self.ds_from_tmpl(new_data)
        #     # print(f"update(new_ds): {new_ds}, {type(new_ds)}")
        #     if new_ds:
        #         # print(f"update(current): {self.pipe.data}, {type(self.pipe.data)}")
        #         # print(f"update(new_ds): {new_ds}, {type(new_ds)}")
        #         self.source.emit(new_ds)
        #         # print(f"update(current) after: {self.pipe.data}")
        #         # print(f"update(new_ds) after: {new_ds}")
        #         # create plot object
        #         self.app = self.create_plots()
        #         # print(f"done creating plots")
        #         self.create_server()
        #         # print(f"done creating server")
        #         return

        new_ds = self.ds_from_tmpl(new_data)
        if new_ds:
            self.source.emit(new_ds)
            if self.pipe.data["time"].size >= 2 and self.server is None:
                # self.app = self.create_plots()
                self.create_server()

        # # if housekeeping from above is done, update stream
        # new_ds = self.ds_from_tmpl(new_data)
        # # print(f"update-new_ds: {new_ds}")
        # self.source.emit(new_ds)
        # # self.source.emit(self.ds_from_tmpl(new_data))

    def create_app(self):
        return self.create_plots()

    def ds_from_tmpl(self, new_data):
        # current_ds = self.pipe.data
        # clist = list(current_ds.coords.keys())
        # vlist = list(current_ds.variables.keys())
        # for c in clist:
        #     if c != "time" and c in vlist:
        #         vlist.remove(c)
        clist, vlist = self.get_var_list()
        # print(f"vlist: {vlist}")
        # print(f"update:data_tmpl: {self.data_tmpl['dims']}, {self.data_tmpl}")
        try:
            for c in clist:
                # print(f"ds_from_tmpl: {c}")
                if c == "time":
                    # print(new_data["variables"][c]["data"])
                    data_val = string_to_datetime(new_data["variables"][c]["data"])
                    # print(data_val)
                else:
                    data_val = new_data["variables"][c]["data"]
                # print(f"ds_from_tmpl: {data_val}")

                if not isinstance(data_val, list):
                    data_val = [data_val]

                # print(f"ds_from_tmpl-coords1: {self.data_tmpl['coords']}")
                self.data_tmpl["coords"][c]["data"] = data_val
                # print(f"ds_from_tmpl-coords2: {self.data_tmpl['coords']}")

            for v in vlist:
                # print(f"ds_from_tmpl: {v}")
                if v == "time":
                    # print(new_data["variables"][v]["data"])
                    data_val = string_to_datetime(new_data["variables"][v]["data"])
                    # print(data_val)
                else:
                    data_val = new_data["variables"][v]["data"]
                if not isinstance(data_val, list):
                    data_val = [data_val]

                # print(f"ds_from_tmpl: {data_val}")
                self.data_tmpl["data_vars"][v]["data"] = data_val

            # print(f"{self.data_tmpl.keys()}, {self.data_tmpl['dims']}")
            # print(f"{self.data_tmpl}")
            new_ds = xr.Dataset.from_dict(self.data_tmpl)
            # print(f"ds_from_tmpl: {new_ds}")
            return new_ds
        except (KeyError, ValueError) as e:
            print(f"ds_from_tmpl error: {e}")
            return None

    def create_plots(self):
        # get list of shapes to create containers for
        shapes = []
        # print(f"create_plots:.5")
        clist, vlist = self.get_var_list()  # exclude_time=True)
        # print(f"create_plots:1")
        self.plot_map = {
            ("time",): {"name": "timeseries-1d", "var-list": [], "plot-container": None}
        }
        # print(f"create_plots:1")

        for name in vlist:
            # print(f"shape: {self.pipe.data[name].coords.keys()}")
            shape = tuple(list(self.pipe.data[name].coords.keys()))
            # print(f"shape: {shape}")
            if shape[0] == "time":
                if shape not in self.plot_map:
                    self.plot_map[shape] = {
                        "name": f"timeseries-2d-{shape[1]}",
                        "var-list": [],
                        "plot_container": None,
                    }
                self.plot_map[shape]["var-list"].append(name)

        # print(f"create_plots:2")
        app = pn.Card(title="Plots", sizing_mode="stretch_width")
        for name, section in self.plot_map.items():

            # print(f"create_plots:3")
            if name == ("time",):  # regular timeseries plot
                # print(name)
                section_card = pn.Card(
                    title="1D Timeseries", sizing_mode="stretch_width"
                )
                # print(section_card)
                add_button = pn.widgets.Button(
                    name="+", button_type="primary", width=30
                )
                # print(add_button)
                add_button.on_click(self.add_timeseries_1d)
                # print(add_button)
                section_card.append(pn.Row(pn.layout.HSpacer(), add_button))
                # print(section_card)
                # print(section)
                section["plot-container"] = section_card
                print(f"section: {section}")
                self.add_timeseries_1d()
                print(f"app1: {app}")
                app.append(section_card)
                print(f"app2: {app}")

                # print(f"create_plots:4")
            elif name == ("time", "diameter"):  # size dist plots
                section_card = pn.Card(
                    title="Size Distribution", sizing_mode="stretch_width"
                )
                # print(section_card)
                add_button = pn.widgets.Button(
                    name="+", button_type="primary", width=30
                )
                # print(add_button)
                add_button.on_click(self.add_size_dist)
                # print(add_button)
                section_card.append(pn.Row(pn.layout.HSpacer(), add_button))
                # print(section_card)
                # print(section)
                section["plot-container"] = section_card
                print(f"section: {section}")
                self.add_size_dist()
                print(f"app1: {app}")
                app.append(section_card)
                print(f"app2: {app}")

            else:
                pass

        # print(f"create_plots:5")
        return app.servable()

    def add_timeseries_1d(self, event=None):
        print(f"event: {event}")
        section_name = ("time",)
        # print(section_name)
        ts1d = self.timeseries_1d(section_name)
        # print(f"ts1d: {ts1d}")
        # self.plot_map[section_name]["plot-container"].append(self.timeseries_1d(section_name))
        self.plot_map[section_name]["plot-container"].append(ts1d)
        # print(f"section: {self.plot_map[section_name]['plot-container']}")

    def timeseries_1d(self, section_name):
        # print(f"timeseries_1d:1")
        vlist = self.plot_map[section_name]["var-list"]
        # vlist = list(self.pipe.data.keys())
        # print(f"vlist: {vlist}")
        # clist,vlist = self.get_var_list()
        # print(f"timeseries_1d:2")
        # var_select = pn.widgets.Select(name="variable", value=vlist[0], options=vlist)
        var_select = pn.widgets.Select(name="variable", options=vlist)
        # print(f"var_select: {var_select}")
        # print(f"timeseries_1d:3")
        plot = pn.bind(self.timeseries_1d_plot, x="time", variable=var_select)
        # print(f"plot: {var_select}, {plot}")
        # print(f"timeseries_1d:4")
        dmap = hv.DynamicMap(plot, streams=[self.pipe]).opts(
            xformatter=self.get_dt_formatter()
        )
        # print(f"dmap: {dmap.vdims}")
        # print(f"timeseries_1d:5")
        # card = pn.Card(var_select, dmap)
        card = pn.Card(var_select, dmap, sizing_mode="stretch_width")
        # print(f"card: {card.objects}")
        return card

    def timeseries_1d_plot(self, data, *args, x="time", variable=""):
        # print(f"ts-1d: {data[variable]}")
        # print(f"ts-1d: {x}, {variable}, {self.get_dt_formatter()}")
        da = data[variable]
        # print(f"ts-1d: {da.values}, {da.values.min()}")
        return data.hvplot(x=x, y=variable, responsive=True, height=250).opts(
            xformatter=self.get_dt_formatter(), shared_axes=False
        )  # , ylim=(data[variable].values.min(),data[variable].values.max()) )

    def add_size_dist(self, event=None):
        print(f"event: {event}")
        section_name = ("time",)
        # print(section_name)
        # ts1d = self.timeseries_1d(section_name)
        size_dist = self.size_dist_2d(section_name)
        # print(f"ts1d: {ts1d}")
        # self.plot_map[section_name]["plot-container"].append(self.timeseries_1d(section_name))
        self.plot_map[section_name]["plot-container"].append(size_dist)
        # print(f"section: {self.plot_map[section_name]['plot-container']}")

    def size_dist_2d(self, section_name):
        # print(f"timeseries_1d:1")
        vlist = self.plot_map[section_name]["var-list"]
        # vlist = list(self.pipe.data.keys())
        # print(f"vlist: {vlist}")
        # clist,vlist = self.get_var_list()
        # print(f"timeseries_1d:2")
        # var_select = pn.widgets.Select(name="variable", value=vlist[0], options=vlist)
        var_select = pn.widgets.Select(name="variable", options=vlist)
        # print(f"var_select: {var_select}")
        # print(f"timeseries_1d:3")
        plot_ts = pn.bind(self.timeseries_size_dist_plot, x="time", y="diameter", variable=var_select)
        # print(f"plot: {var_select}, {plot}")
        # print(f"timeseries_1d:4")
        dmap_ts = hv.DynamicMap(plot_ts, streams=[self.pipe]).opts(
            xformatter=self.get_dt_formatter(), logy=True
        )

        plot_scan = pn.bind(self.scan_size_dist_plot, x="diameter", variable=var_select)
        # print(f"plot: {var_select}, {plot}")
        # print(f"timeseries_1d:4")
        dmap_scan = hv.DynamicMap(plot_scan, streams=[self.pipe]).opts(
            logx=True
        )

        # print(f"dmap: {dmap.vdims}")
        # print(f"timeseries_1d:5")
        # card = pn.Card(var_select, dmap)
        card = pn.Card(var_select, pn.Row(dmap_ts,dmap_scan), sizing_mode="stretch_width")
        # print(f"card: {card.objects}")
        return card


    def timeseries_size_dist_plot(self, data, *args, x="time", y="diameter", variable=""):
        # da = data[variable]
        # print(f"ts-1d: {da.values}, {da.values.min()}")
        return data.hvplot.quadmesh(x=x, y=y, z=variable, responsive=True, height=250).opts(
            xformatter=self.get_dt_formatter(), shared_axes=False, ylog=True
        )  # , ylim=(data[variable].values.min(),data[variable].values.max()) )

    def scan_size_dist_plot(self, data, *args, x="diameter", variable=""):
        y = data[variable].values[-1]
        x = data[x].values
        # print(f"ts-1d: {da.values}, {da.values.min()}")
        return data.hvplot(x=x, y=y, responsive=True, height=250).opts(
            xformatter=self.get_dt_formatter(), shared_axes=False, logy=True
        )  # , ylim=(data[variable].values.min(),data[variable].values.max()) )
