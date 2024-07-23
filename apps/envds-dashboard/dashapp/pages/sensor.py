from datetime import datetime, timezone
import json
import dash
import plotly.express as px
import plotly.graph_objs as go
from dash import (
    html,
    callback,
    dcc,
    Input,
    Output,
    dash_table,
    State,
    MATCH,
    ALL,
    Patch,
)
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
from pydantic import BaseSettings
from ulid import ULID
import dash_ag_grid as dag
import pandas as pd
# import pymongo
from collections import deque

from envds.daq.db import (
    SensorTypeRegistration,
    SensorRegistration,
    SensorDataRecord,
    # init_db_models,
    # register_sensor_type,
    # register_sensor,
    get_sensor_type_registration,
    get_sensor_registration,
    get_all_sensor_registration,
    get_sensor_registration_by_pk,
    get_all_sensor_type_registration,
    get_sensor_type_registration_by_pk,
    get_sensor_data,
)

dash.register_page(
    __name__,
    path_template="/sensor/<sensor_id>",
    title="UAS-DAQ Sensors",  # , prevent_initial_callbacks=True
)


# class Settings(BaseSettings):
#     host: str = "0.0.0.0"
#     port: int = 8787
#     debug: bool = False
#     knative_broker: str = (
#         "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default"
#     )
#     mongodb_data_user_name: str = ""
#     mongodb_data_user_password: str = ""
#     mongodb_registry_user_name: str = ""
#     mongodb_registry_user_password: str = ""
#     mongodb_data_connection: str = (
#         "mongodb://uasdaq:password@uasdaq-mongodb-0.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-1.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-2.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017/data?replicaSet=uasdaq-mongodb&ssl=false"
#     )
#     mongodb_registry_connection: str = (
#         "mongodb://uasdaq:password@uasdaq-mongodb-0.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-1.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-2.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017/registry?replicaSet=uasdaq-mongodb&ssl=false"
#     )
#     # erddap_http_connection: str = (
#     #     "http://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
#     # )
#     # erddap_https_connection: str = (
#     #     "https://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
#     # )
#     # erddap_author: str = "fake_author"

#     dry_run: bool = False

#     class Config:
#         env_prefix = "DASHBOARD_"
#         case_sensitive = False


# config = Settings()

# # TODO: add readOnly user for this connection

# # combine secrets to get complete connection string
# if "<username>" in config.mongodb_data_connection:
#     mongodb_data_conn = config.mongodb_data_connection.replace(
#         "<username>", config.mongodb_data_user_name
#     )
#     config = config.copy(update={"mongodb_data_connection": mongodb_data_conn})

# if "<password>" in config.mongodb_data_connection:
#     mongodb_data_conn = config.mongodb_data_connection.replace(
#         "<password>", config.mongodb_data_user_password
#     )
#     config = config.copy(update={"mongodb_data_connection": mongodb_data_conn})

# if "<username>" in config.mongodb_registry_connection:
#     mongodb_registry_conn = config.mongodb_registry_connection.replace(
#         "<username>", config.mongodb_registry_user_name
#     )
#     config = config.copy(update={"mongodb_registry_connection": mongodb_registry_conn})

# if "<password>" in config.mongodb_registry_connection:
#     mongodb_registry_conn = config.mongodb_registry_connection.replace(
#         "<password>", config.mongodb_registry_user_password
#     )
#     config = config.copy(update={"mongodb_registry_connection": mongodb_registry_conn})

# class DBClient:
#     def __init__(self, connection: str, db_type: str = "mongodb") -> None:
#         self.db_type = db_type
#         self.client = None
#         self.connection = connection

#     def connect(self):
#         if self.db_type == "mongodb":
#             self.connect_mongo()
#         # return self.client

#     def connect_mongo(self):
#         if not self.client:
#             try:
#                 self.client = pymongo.MongoClient(
#                     # self.client = AsyncIOMotorClient(
#                     self.connection,
#                     # connect=True,
#                     # tls=True,
#                     # tlsAllowInvalidCertificates=True
#                 )
#             except pymongo.errors.ConnectionError:
#                 self.client = None
#             # L.info("mongo client", extra={"connection": self.connection, "client": self.client})
#             # L.info(await self.client.server_info())
#         # return self.client

#     def get_db(self, database: str):
#         self.connect()
#         if self.client:
#             return self.client[database]
#         return None

#     def get_collection(self, database: str, collection: str):
#         # L.info("get_collection")
#         db = self.get_db(database)
#         # L.info(f"get_collection:db = {db}")
#         if db is not None:
#             try:
#                 db_coll = db[collection]
#                 # L.info(f"get_collection:db:collection = {db_coll}")
#                 return db_coll
#             except Exception as e:
#                 print(f"get_collection error: {e}")
#         return None

#     def find_one(self, database: str, collection: str, query: dict):
#         self.connect()
#         if self.client:
#             # db = self.client[database]
#             # db_collection = db[collection]
#             db_collection = self.get_collection(
#                 database=database, collection=collection
#             )
#             result = db_collection.find_one(query)
#             if result:
#                 update = {"last_update": datetime.now(tz=timezone.utc)}
#                 self.client.update_one(database, collection, result, update)
#             return result
#         return None

#     def find(
#         self, database: str, collection: str, query: dict, sort=None, refresh=True
#     ):
#         self.connect()
#         if self.client:
#             # db = self.client[database]
#             # db_collection = db[collection]
#             db_collection = self.get_collection(
#                 database=database, collection=collection
#             )
#             if sort:
#                 find_result = db_collection.find(query).sort(sort)
#             else:
#                 find_result = db_collection.find(query)
#             # print(f"find result: {result}")
#             result = []
#             for r in find_result:
#                 result.append(r)
#                 # print(f"r: {r}")

#             if result and refresh:
#                 for r in result:
#                     # print(f"r: {r}")
#                     update = {"last_update": datetime.now(tz=timezone.utc)}
#                     self.update_one(database, collection, r, update)

#             return result
#         return None

#     def insert_one(self, database: str, collection: str, document: dict):
#         self.connect()
#         if self.client:
#             db = self.client[database]
#             sensor_defs = db[collection]
#             result = sensor_defs.insert_one(document)
#             return result
#         return None

#     def update_one(
#         self,
#         database: str,
#         collection: str,
#         document: dict,
#         update: dict,
#         filter: dict = None,
#         upsert=False,
#     ):
#         self.connect()
#         if self.client:
#             db = self.client[database]
#             sensor = db[collection]
#             if filter is None:
#                 filter = document
#             set_update = {"$set": update}
#             if upsert:
#                 set_update["$setOnInsert"] = document
#             result = sensor.update_one(filter=filter, update=set_update, upsert=upsert)
#             return result
#         return None


# db_data_client = DBClient(connection=config.mongodb_data_connection)
# db_registry_client = DBClient(connection=config.mongodb_registry_connection)


# websocket = WebSocket(
#     id="ws-sensor", url=f"ws://uasdaq.pmel.noaa.gov/uasdaq/dashboard/ws/sensor/main"
# )
ws_send_buffer = html.Div(id="ws-send-instance-buffer", style={"display": "none"})


def build_tables(layout_options):

    table_list = []
    print(f"build_tables: {layout_options}")
    for ltype, dims in layout_options.items():
        for dim, options in dims.items():
            title = "Data"
            if ltype == "layout-1d":
                title = f"Data 1-D ({dim})"

                # TODO: make the ids work for multiple dims
                table_list.append(
                    dbc.AccordionItem(
                        [
                            dag.AgGrid(
                                id={"type": "data-table-1d", "index": dim},
                                rowData=[],
                                columnDefs=layout_options["layout-1d"][dim][
                                    "table-column-defs"
                                ],
                                columnSizeOptions="autoSize",  # "autoSize", "autoSizeSkip", "sizeToFit", "responsiveSizeToFit"
                            )
                        ],
                        title=title,
                    )
                )
                print(f"build_tables: {table_list}")

            elif ltype == "layout-2d":
                title = f"Data 2-D (time, {dim})"
                table_list.append(
                    dbc.AccordionItem(
                        [
                            dag.AgGrid(
                                id={"type": "data-table-2d", "index": f"time::{dim}"},
                                rowData=[],
                                columnDefs=layout_options["layout-2d"][dim][
                                    "table-column-defs"
                                ],
                                columnSizeOptions="autoSize",  # "autoSize", "autoSizeSkip", "sizeToFit", "responsiveSizeToFit"
                            )
                        ],
                        title=title,
                    )
                )

    print(f"build_tables: {table_list}")

    return table_list


# def build_graph_1d(dropdown_list):
def build_graph_1d(dropdown_list, xaxis="time", yaxis=""):

    graph = dbc.Card(
        children=[
            dbc.CardHeader(
                children=[
                    dcc.Dropdown(
                        id={"type": "graph-1d-dropdown", "index": xaxis},
                        options=dropdown_list,
                        value="",
                    )
                ]
            ),
            dcc.Graph(
                id={"type": "graph-1d", "index": xaxis},
                figure=go.Figure(
                    data=go.Scatter(x=[], y=[], type="scatter")
                    # {
                    #     "x": [],
                    #     "y": [],
                    #     "type": "scatter",
                    # }
                ),
                style={"height": 300},
            ),
        ]
    )

    return graph


def build_graph_2d(dropdown_list, xaxis="time", yaxis="", zaxis=""):

    content = dbc.Row(
        children=[
            dbc.Button("Submit", {"type": "graph-2d-z-axis-submit", "index": f"{xaxis}::{yaxis}"}),
            dbc.Label("z-axis min:"),
            dbc.Col(
                dbc.Input(
                    type="number",
                    id={"type": "graph-2d-z-axis-min", "index": f"{xaxis}::{yaxis}"},
                )
            ),
            dbc.Label("z-axis max:"),
            dbc.Col(
                dbc.Input(
                    type="number",
                    id={"type": "graph-2d-z-axis-max", "index": f"{xaxis}::{yaxis}"},
                )
            ),
        ]
    )

    # axes_collapse = html.Div(
    #     [

    #         dbc.Button(
    #             "Axes Settings",
    #             id={"type": "graph-2d-axes-settings", "index": f"{xaxis}::{yaxis}"},
    #             className="mb-3",
    #             # color="primary",
    #             n_clicks=0,
    #         ),
    #         dbc.Collapse(
    #             dbc.Card(children=[content]),
    #             id={"type": "graph-2d-axes-collapse", "index": f"{xaxis}::{yaxis}"},
    #             is_open=False,
    #         ),
    #     ]
    # )

    axes_settings = dbc.Accordion(
        children=[
            dbc.AccordionItem(
                [dbc.Card(children=[content])],
                title="Axes Settings",
                # start_collapsed=True
            )
        ],
        start_collapsed=True
    )

    graph = dbc.Card(
        children=[
            dbc.CardHeader(
                children=[
                    dcc.Dropdown(
                        id={"type": "graph-2d-dropdown", "index": f"{xaxis}::{yaxis}"},
                        options=dropdown_list,
                        value="",
                    )
                ]
            ),
            dbc.Row(
                children=[
                    axes_settings,
                    dbc.Col(
                        dcc.Graph(
                            id={
                                "type": "graph-2d-heatmap",
                                "index": f"{xaxis}::{yaxis}",
                            },
                            # figure=go.Figure(
                            #     data=go.Heatmap(x=[], y=[], z=[], type="heatmap")
                            # ),
                            # figure=[
                            #     {
                            #         "x": [],
                            #         "y": [],
                            #         "type": "scatter",
                            #     }
                            #     }
                            # ],
                            style={"height": 500},
                        )
                    ),
                    dbc.Col(
                        dcc.Graph(
                            id={"type": "graph-2d-line", "index": f"{xaxis}::{yaxis}"},
                            # figure=go.Figure(
                            #     data=go.Line(x=[], y=[], type="line")
                            # ),
                            # figure=[
                            #     {
                            #         "x": [],
                            #         "y": [],
                            #         "type": "scatter",
                            #     }
                            # ],
                            style={"height": 500},
                        )
                    ),
                ]
            ),
            # dbc.Col(children=[
            #     dcc.Graph(
            #         id={"type": "graph-2d-heatmap", "index": f"{xaxis}::{yaxis}"},
            #         # figure=go.Figure(
            #         #     data=go.Heatmap(x=[], y=[], z=[], type="heatmap")
            #         # ),
            #         # figure=[
            #         #     {
            #         #         "x": [],
            #         #         "y": [],
            #         #         "type": "scatter",
            #         #     }
            #         #     }
            #         # ],
            #         style={"height": 600},
            #     ),
            #     dcc.Graph(
            #         id={"type": "graph-2d-line", "index": f"{xaxis}::{yaxis}"},
            #         # figure=go.Figure(
            #         #     data=go.Line(x=[], y=[], type="line")
            #         # ),
            #         # figure=[
            #         #     {
            #         #         "x": [],
            #         #         "y": [],
            #         #         "type": "scatter",
            #         #     }
            #         # ],
            #         style={"height": 600},
            #     )
            # ])
            # dcc.Graph(
            #     id="graph-2d",
            #     figure=go.Figure(
            #         data=go.Heatmap(x=[], y=[], z=[], type="heatmap")
            #     ),
            #     # figure=[
            #     #     {
            #     #         "x": [],
            #     #         "y": [],
            #     #         "type": "scatter",
            #     #     }
            #     # ],
            #     style={"height": 300},
            # ),
        ]
    )

    return graph


def build_graph_settings_2d():

    collapse = html.Div(
        [
            dbc.Button(
                "Graph Settings",
                id="collapse-button",
                className="mb-3",
                color="primary",
                n_clicks=0,
            ),
            dbc.Collapse(
                dbc.Card(dbc.CardBody("This content is hidden in the collapse")),
                id="collapse",
                is_open=False,
            ),
        ]
    )


def build_graphs(layout_options):

    graph_list = []
    print(f"build_graphs: {layout_options}")
    for ltype, dims in layout_options.items():
        for dim, options in dims.items():
            title = "Plots"
            if ltype == "layout-1d":
                title = f"Plots 1-D ({dim})"

                # TODO: make the ids work for multiple dims
                graph_list.append(
                    dbc.AccordionItem(
                        [
                            dbc.Row(
                                children=[
                                    build_graph_1d(
                                        layout_options["layout-1d"][dim][
                                            "variable-list"
                                        ],
                                        xaxis=dim,
                                    )
                                ]
                            )
                        ],
                        title=title,
                    )
                )
                print(f"build_graphs: {graph_list}")

            elif ltype == "layout-2d":
                title = f"Data 2-D (time, {dim})"
                graph_list.append(
                    dbc.AccordionItem(
                        [
                            dbc.Row(
                                children=[
                                    build_graph_2d(
                                        layout_options["layout-2d"][dim][
                                            "variable-list"
                                        ],
                                        xaxis="time",
                                        yaxis=dim,
                                    )
                                ]
                            )
                        ],
                        title=title,
                    )
                )

    print(f"build_tables: {graph_list}")

    return graph_list


def layout(sensor_id=None):
    print(f"get_layout: {sensor_id}")
    sensor_definition = None
    if sensor_id:
        parts = sensor_id.split("::")
        # print(f"get_layout: {parts}")
        sensor_meta = {
            "sensor-id": sensor_id,
            "make": parts[0],
            "model": parts[1],
            "serial_number": parts[2],
        }
        # print(f"get_layout: {sensor_meta}")
        # query = {"make": sensor_meta["make"], "model": sensor_meta["model"]}
        # # print(f"get_layout: {query}")
        # results = db_registry_client.find(
        #     database="registry", collection="sensor_definition", query=query
        # )
        # if len(results) > 0:
        #     sensor_definition = results[0]
        #     if len(results) > 1:
        #         for sdef in results[1:]:
        #             try:
        #                 if sdef["version"] > sensor_definition["version"]:
        #                     sensor_definition = sdef
        #             except KeyError:
        #                 pass
            # else:
            #     sensor_definition = None
        
        sensor_type = get_sensor_type_registration(make=sensor_meta["make"], model=sensor_meta["model"])

        # print(f"sensor def: {sdef}")
    else:
        # sensor_id = "AerosolDynamics::MAGIC250::142"
        # parts = sensor_id.split("::")
        sensor_meta = {}
        # sensor_definition = None
        sensor_type = None

    layout_options = {
        "layout-1d": {"time": {"table-column-defs": [], "variable-list": []}}
    }
    column_defs_1d = []  # deque([], maxlen=10)
    dropdown_list_1d = []
    column_defs_1d = []  # deque([], maxlen=10)
    dropdown_list_2d = []
    # if sensor_definition:
    if sensor_type and "metadata" in sensor_type:
        sensor_definition = sensor_type["metadata"]
        try:
            dimensions = sensor_definition["dimensions"]
            is_2d = False
            if len(dimensions.keys()) > 1:
                is_2d = True
                if "layout-2d" not in layout_options:
                    layout_options["layout-2d"] = (
                        {}
                    )  # {dim_2d: {"table-column-defs": [], "variable-list": []}}

                # for d in dimensions.keys():
                #     if d == "time":
                #         continue
                #     if "columns_2d" not in graph_options:
                #         graph_options["columns_2d"] = dict()
                #     graph_options["columns_2d"] = {d:[]}

            print(f"layout: {layout_options}")
            if is_2d:
                for d in dimensions.keys():
                    if d == "time":
                        cd = {
                            "field": "time",
                            "headerName": "Time",
                            "filter": False,
                            "cellDataType": "text",
                            "pinned": "left",
                        }
                        layout_options["layout-1d"]["time"]["table-column-defs"].append(
                            cd
                        )

                    # if d != "time":
                    else:
                        layout_options["layout-2d"][d] = {
                            "table-column-defs": [],
                            "variable-list": [],
                        }
                        ln = d
                        try:
                            ln = sensor_definition["attributes"][d]["long_name"]["data"]
                        except KeyError:
                            pass

                        print(f"layout: {ln}")
                        data_type = "text"
                        try:
                            dtype = sensor_definition["variables"][d]["type"]
                            if dtype in ["float", "double", "int"]:
                                data_type = "number"
                            elif dtype in ["str", "string", "char"]:
                                data_type = "text"
                            elif dtype in ["bool"]:
                                data_type = "boolean"
                        except KeyError:
                            pass
                        print(f"layout: {data_type}")

                        cd = {
                            "field": d,
                            "headerName": ln,
                            "filter": False,
                            "cellDataType": data_type,
                            "pinned": "left",
                        }
                        layout_options["layout-2d"][d]["table-column-defs"].append(cd)
                        print(f"layout: {layout_options}")
            else:
                if "time" in dimensions:
                    # column_defs_1d.append(
                    cd = {
                        "field": "time",
                        "headerName": "Time",
                        "filter": False,
                        "cellDataType": "text",
                        "pinned": "left",
                    }
                    layout_options["layout-1d"]["time"]["table-column-defs"].append(cd)
                    print(f"layout: {layout_options}")

            for name, var in sensor_definition["variables"].items():
                if name in dimensions:
                    continue
                if "shape" not in var:
                    continue
                if "time" not in var["shape"]:
                    continue
                # if len(var["shape"]) > 1 or "time" not in var["shape"]:
                #     continue

                long_name = name
                ln = var["attributes"].get("long_name", None)
                if ln:
                    long_name = ln.get("data", name)

                # get data type
                dtype = var.get("type", "unknown")
                print(f"dtype = {dtype}")
                data_type = "text"
                if dtype in ["float", "double", "int"]:
                    data_type = "number"
                elif dtype in ["str", "string", "char"]:
                    data_type = "text"
                elif dtype in ["bool"]:
                    data_type = "boolean"

                # column_defs_1d.append(
                cd = {
                    "field": name,
                    "headerName": long_name,
                    "filter": False,
                    "cellDataType": data_type,
                }
                # )

                if is_2d and len(var["shape"]) == 2:
                    dim_2d = [d for d in var["shape"] if d != "time"][0]
                    layout_options["layout-2d"][dim_2d]["table-column-defs"].append(cd)
                else:
                    layout_options["layout-1d"]["time"]["table-column-defs"].append(cd)

            for ltype, dims in layout_options.items():
                # for gtype, options in layout_options.items():
                for dim, options in dims.items():
                    for cd in options["table-column-defs"]:
                        if cd["field"] in dimensions:
                            continue
                        if cd["cellDataType"] != "number":
                            continue
                        layout_options[ltype][dim]["variable-list"].append(
                            {"label": cd["field"], "value": cd["field"]}
                        )

            # # dropdown_list = []
            # for cd in column_defs_1d:
            #     if cd["field"] == "time":
            #         continue
            #     if cd["cellDataType"] != "number":
            #         continue
            #     dropdown_list_1d.append({"label": cd["field"], "value": cd["field"]})

        except KeyError as e:
            print(f"build column_defs error: {e}")

    # print("here:1")
    layout = html.Div(
        [
            html.H1(f"Sensor: {sensor_id}"),
            # get_button,
            # build_tables(layout_options)
            dbc.Accordion(
                build_tables(layout_options),
                # [
                #     dbc.AccordionItem(
                #         [
                #             dag.AgGrid(
                #                 id="data-table-1d",
                #                 rowData=[],
                #                 columnDefs=layout_options["layout-1d"]["time"]["table-column-defs"],
                #                 columnSizeOptions="autoSize",  # "autoSize", "autoSizeSkip", "sizeToFit", "responsiveSizeToFit"
                #             )
                #         ],
                #         title="Data: 1-D",
                #     ),
                #     # dbc.AccordionItem(
                #     #     [
                #     #         dag.AgGrid(
                #     #             id="active-sensor-table",
                #     #             rowData=[],
                #     #             columnDefs=[
                #     #                 {
                #     #                     "field": "make",
                #     #                     "headerName": "Make/Mfg",
                #     #                     "filter": True,
                #     #                 },
                #     #                 {
                #     #                     "field": "model",
                #     #                     "headerName": "Model",
                #     #                     "filter": True,
                #     #                 },
                #     #                 {
                #     #                     "field": "serial_number",
                #     #                     "headerName": "Serial Number",
                #     #                     "filter": True,
                #     #                 },
                #     #                 {
                #     #                     "field": "sampling_system",
                #     #                     "headerName": "Sampling System",
                #     #                     "filter": True,
                #     #                 },
                #     #             ],
                #     #         )
                #     #     ],
                #     #     title="Active Sensors",
                #     # ),
                # ],
                id="sensor-data-accordion",
            ),
            dbc.Accordion(
                build_graphs(layout_options),
                # [
                #     dbc.AccordionItem(
                #         [
                #             dbc.Row(
                #                 children=[
                #                     build_graph_1d(
                #                         layout_options["layout-1d"]["time"][
                #                             "variable-list"
                #                         ]
                #                     )
                #                     # dbc.Card(
                #                     #     children=[
                #                     #         dbc.CardHeader(
                #                     #             children=[
                #                     #                 dcc.Dropdown(
                #                     #                     id="graph-1d-dropdown",
                #                     #                     options=dropdown_list_1d,
                #                     #                     value=""
                #                     #                 )
                #                     #             ]
                #                     #         ),
                #                     #         dcc.Graph(
                #                     #             id="graph-1d",
                #                     #             figure=[
                #                     #                 {
                #                     #                     "x": [],
                #                     #                     "y": [],
                #                     #                     "type": "scatter",
                #                     #                 }
                #                     #             ],
                #                     #             style={"height": 300},
                #                     #         ),
                #                     #     ]
                #                     # )
                #                 ]
                #             )
                #         ],
                #         title="Data: 1-D",
                #     ),
                #     # dbc.AccordionItem(
                #     #     [
                #     #         dbc.Row(
                #     #             children=[
                #     #                 build_graph_2d(graph_options["layout-2d"]["variable-list"])
                #     #             ]
                #     #         )
                #     #     ],
                #     #     title="Data: 1-D",
                #     # ),
                # ],
                id="sensor-plot-accordion",
            ),
            WebSocket(
                id="ws-sensor-instance",
                url=f"ws://10.55.169.1/envds/dashboard/ws/sensor/{sensor_id}",
            ),
            ws_send_buffer,
            dcc.Store(id="sensor-definition", data=sensor_definition),
            dcc.Store(id="sensor-meta", data=sensor_meta),
            dcc.Store(id="graph-axes", data={}),
            dcc.Store(id="sensor-data-buffer", data={}),
            dcc.Store(id="sensor-settings-buffer", data={}),
            dcc.Store(id="sensor-statis-buffer", data={}),
            # dcc.Interval(id="test-interval", interval=(10*1000)),
            # dcc.Interval(
            #     id="table-update-interval", interval=(5 * 1000), n_intervals=0
            # ),
            # dcc.Interval(id="active-sensor-update-interval", interval=(5*1000), n_intervals=0),
            # html.Div(id="test-output")
        ]
    )
    # print("here:2")

    request = {"client-request": "start-updates"}
    # print("here:3")
    # print(f"sent request: {request}")
    # ws_send_buffer.children = json.dumps(request)
    # print("here:4")
    # websocket.send("test programatically")
    return layout


# layout = get_layout  # ()

# @callback(
#     Output("test-output", "children"),
#     Input("test-interval", "n_intervals")
# )
# def test_read(num_intervals):

#     docs = []
#     db_registry_client.connect()
#     if db_registry_client:
#         sensor_def_registry = db_registry_client.get_collection("registry", "sensor_definition")
#         for doc in sensor_def_registry.find().sort("_id"):
#             if doc:
#                 docs.append(doc)
#             print(f"sensor defintion: {doc}")
#         print(f"Number of docs: {len(docs)}, {docs}")
#     return doc


# @callback(
#     Output("sensor-defs-table", "rowData"),
#     Input("table-update-interval", "n_intervals"),
#     State("sensor-defs-table", "rowData"),
# )
# def update_sensor_definitions(count, table_data):
#     # print(f"sensor_def: {count}")
#     update = False
#     new_data = []
#     try:
#         db_registry_client.connect()
#         if db_registry_client:
#             sensor_def_registry = db_registry_client.get_collection(
#                 "registry", "sensor_definition"
#             )
#             for doc in sensor_def_registry.find():
#                 if doc is not None:
#                     # print(f"doc: {doc}")
#                     id = doc["_id"]
#                     make = doc["make"]
#                     model = doc["model"]
#                     version = doc["version"]

#                     sensor_def = {
#                         "sensor-def-id": id,
#                         "make": make,
#                         "model": model,
#                         "version": version,
#                     }
#                     if sensor_def not in table_data:
#                         table_data.append(sensor_def)
#                         update = True
#                     new_data.append(sensor_def)

#             remove_data = []
#             for index, data in enumerate(table_data):
#                 if data not in new_data:
#                     update = True
#                     remove_data.insert(0,index)
#             for index in remove_data:
#                 table_data.pop(index)

#             if update:
#                 return table_data
#             else:
#                 return dash.no_update

#     except Exception as e:
#         print(f"update_sensor_definitions error: {e}")
#         return dash.no_update


# @callback(
#     Output("active-sensor-table", "rowData"),
#     Input("table-update-interval", "n_intervals"),
#     State("active-sensor-table", "rowData"),
# )
# def update_active_sensors(count, table_data):

#     # print(f"active_sensor: {count}")
#     update = False
#     new_data = []
#     try:
#         db_registry_client.connect()
#         if db_registry_client:
#             # print(db_registry_client)
#             sensor_registry = db_registry_client.get_collection("registry", "sensor")
#             # print(sensor_registry)
#             for doc in sensor_registry.find():
#                 if doc is not None:
#                     # print(f"doc: {doc}")
#                     make = doc["make"]
#                     model = doc["model"]
#                     serial_number = doc["serial_number"]
#                     version = doc["version"]
#                     id = "::".join([make, model, serial_number])
#                     sampling_system = "unknown"

#                     sensor = {
#                         "sensor-id": id,
#                         "make": make,
#                         "model": model,
#                         "serial_number": serial_number,
#                         "sampling_system": sampling_system,
#                     }
#                     if sensor not in table_data:
#                         table_data.append(sensor)
#                         update = True
#                     new_data.append(sensor)

#             remove_data = []
#             for index, data in enumerate(table_data):
#                 if data not in new_data:
#                     update = True
#                     remove_data.insert(0,index)
#             for index in remove_data:
#                 table_data.pop(index)

#             if update:
#                 return table_data
#             else:
#                 return dash.no_update

#     except Exception as e:
#         print(f"update_active_sensors error: {e}")
#         return dash.no_update


@callback(
    # [Output({"type": "graph-1d", "index": MATCH}, "figure"), Output("graph-axes", "data")],
    Output(
        {"type": "graph-1d", "index": MATCH}, "figure"
    ),  # Output("graph-axes", "data")],
    Input({"type": "graph-1d-dropdown", "index": MATCH}, "value"),
    [
        State("sensor-meta", "data"),
        State("graph-axes", "data"),
        State("sensor-definition", "data"),
        State({"type": "graph-1d-dropdown", "index": MATCH}, "id"),
    ],
)
def select_graph_1d(y_axis, sensor_meta, graph_axes, sensor_definition, graph_id):
    print(f"select_graph_1d: {y_axis}, {sensor_meta}, {graph_axes}")
    # print(f"current_fig: {current_fig}")
    try:
        if "graph-1d" not in graph_axes:
            graph_axes["graph-1d"] = dict()
        graph_axes["graph-1d"][graph_id["index"]] = {"x-axis": "time", "y-axis": y_axis}
        print(f"select_graph_1d: {graph_axes}")

        x = []
        y = []
        query = {
            "make": sensor_meta["make"],
            "model": sensor_meta["model"],
            "serial_number": sensor_meta["serial_number"],
        }
        sort = {"variables.time.data": 1}
        # results = db_data_client.find("data", "sensor", query, sort)
        results = get_sensor_data(make=sensor_meta["make"], model=sensor_meta["model"], serial_number=sensor_meta["serial_number"])
        # print(f"results: {results}")
        if results is None or len(results) == 0:
            print("results = None")
            # return [{"x": [], "y": [], "type": "scatter"}, graph_axes]
            return {"x": [], "y": [], "type": "scatter"}  # , graph_axes]
        if results and len(results) > 0:
            print("results = good")
            for doc in results:
                try:
                    x.append(doc["data"]["variables"]["time"]["data"])
                    y.append(doc["data"]["variables"][y_axis]["data"])
                except KeyError:
                    continue

        # print(f"x,y: {x}, {y}")
        # # fig = go.Figure(data=[go.Scatter(x=x, y=y)])
        # print(f"go fig: {fig}")
        # fig = dict(data=[{'x': x, 'y': y}])
        units = ""
        try:
            units = f'({sensor_definition["variables"][y_axis]["attributes"]["units"]["data"]})'
        except KeyError:
            pass

        # fig = {
        #     "data": [{"x": x, "y": y, "type": "scatter"}],
        #     "layout": {
        #         "xaxis": {"title": "Time"},
        #         "yaxis": {"title": f"{y_axis} {units}"},
        #     },
        # }
        fig = go.Figure(
            data=go.Scatter(x=x, y=y, type="scatter"),
            layout={
                "xaxis": {"title": "Time"},
                "yaxis": {"title": f"{y_axis} {units}"},
            },
        )
        # print(f"go fig: {fig}")
        # return [fig, graph_axes]
        return fig  # , graph_axes]
    except Exception as e:
        print(f"select_graph_1d error: {e}")
        # return [dash.no_update, dash.no_update]
        return dash.no_update  # , dash.no_update]


@callback(
    # [Output({"type": "graph-1d", "index": MATCH}, "figure"), Output("graph-axes", "data")],
    [
        Output(
            {"type": "graph-2d-heatmap", "index": MATCH}, "figure", allow_duplicate=True
        ),
        Output(
            {"type": "graph-2d-line", "index": MATCH}, "figure", allow_duplicate=True
        ),
    ],
    Input({"type": "graph-2d-dropdown", "index": MATCH}, "value"),
    [
        State("sensor-meta", "data"),
        State("graph-axes", "data"),
        State("sensor-definition", "data"),
        State({"type": "graph-2d-dropdown", "index": MATCH}, "id"),
    ],
    prevent_initial_call=True,
)
def select_graph_2d(z_axis, sensor_meta, graph_axes, sensor_definition, graph_id):
    print(f"select_graph_2d: {z_axis}, {sensor_meta}, {graph_axes}, {graph_id}")
    # print(f"current_fig: {current_fig}")
    try:
        if "graph-2d" not in graph_axes:
            graph_axes["graph-2d"] = dict()
        y_axis = graph_id["index"].split("::")[1]
        use_log = False
        if y_axis == "diameter":
            use_log = True
        graph_axes["graph-2d"][graph_id["index"]] = {
            "x-axis": "time",
            "y-axis": y_axis,
            "z-axis": z_axis,
        }
        print(f"select_graph_2d: {graph_axes}")

        x = []
        y = []
        z = []
        orig_z = []
        query = {
            "make": sensor_meta["make"],
            "model": sensor_meta["model"],
            "serial_number": sensor_meta["serial_number"],
        }
        sort = {"variables.time.data": 1}
        # results = db_data_client.find("data", "sensor", query, sort, refresh=False)
        results = get_sensor_data(make=sensor_meta["make"], model=sensor_meta["model"], serial_number=sensor_meta["serial_number"])
        print(f"2d results: {results}")
        if results is None or len(results) == 0:
            print("results = None")
            # return [{"x": [], "y": [], "type": "scatter"}, graph_axes]
            # return {"x": [], "y": [], "type": "scatter"}#, graph_axes]
            raise PreventUpdate

        elif results and len(results) > 0:
            print("results = good")
            for doc in results:
                try:
                    x.append(doc["data"]["variables"]["time"]["data"])
                    y.append(doc["data"]["variables"][y_axis]["data"])
                    orig_z.append(doc["data"]["variables"][z_axis]["data"])
                except KeyError:
                    continue

        # print(f"x,y: {x}, {y}")
        # # fig = go.Figure(data=[go.Scatter(x=x, y=y)])
        # print(f"go fig: {fig}")
        # fig = dict(data=[{'x': x, 'y': y}])
        units = ""
        try:
            y_units = f'({sensor_definition["variables"][y_axis]["attributes"]["units"]["data"]})'
            z_units = f'({sensor_definition["variables"][z_axis]["attributes"]["units"]["data"]})'
        except KeyError:
            pass

        # fig = {
        #     "data": [{"x": x, "y": y, "type": "scatter"}],
        #     "layout": {
        #         "xaxis": {"title": "Time"},
        #         "yaxis": {"title": f"{y_axis} {units}"},
        #     },
        # }
        if isinstance(y[-1], list):
            y = y[-1]

        for yi, yval in enumerate(y):
            # z.append([])
            new_z = []
            for xi, xval in enumerate(x):
                new_z.append(orig_z[xi][yi])
            z.append(new_z)

        heatmap = go.Figure(
            data=go.Heatmap(
                x=x, y=y, z=z, type="heatmap", colorscale="Rainbow"
            ),
            # data=[{"x": x, "y": y, "z": z, "type": "heatmap"}],
            layout={
                "xaxis": {"title": "Time"},
                "yaxis": {"title": f"{y_axis} {y_units}"},
                # "yaxis": {"title": f"{y_axis} {y_units}"},
                # "colorscale": "rainbow"
            },
        )
        if use_log:
            heatmap.update_yaxes(type="log")
            heatmap.update_layout(coloraxis=dict(cmax=None, cmin=None))
        print(f"heatmap figure: {heatmap}")
        scatter = go.Figure(
            # data=go.Scatter(x=y, y=z[-1], type="scatter"),
            data=[{"x": y, "y": z[-1], "type": "scatter"}],
            layout={
                "xaxis": {"title": f"{y_axis} {y_units}"},
                "yaxis": {"title": f"{z_axis} {z_units}"},
                "title": str(x[-1]),
                # "yaxis": {"title": f"{y_axis} {y_units}"},
                # "colorscale": "rainbow"
            },
        )
        if use_log:
            scatter.update_xaxes(type="log")
        print(f"scatter figure: {scatter}")

        # print(f"go fig: {fig}")
        # return [fig, graph_axes]
        return [heatmap, scatter]  # , graph_axes]
    except Exception as e:
        print(f"select_graph_2d error: {e}")
        # return [dash.no_update, dash.no_update]
        raise PreventUpdate
        # return [dash.no_update, dash.no_update]


@callback(Output("sensor-data-buffer", "data"), Input("ws-sensor-instance", "message"))
def update_sensor_data_buffer(e):
    if e is not None and "data" in e:
        try:
            msg = json.loads(e["data"])
            if msg:
                return msg
        except Exception as e:
            print(f"data buffer update error: {e}")
            # return dash.no_update
            # return dash.no_update
    return dash.no_update


@callback(
    Output({"type": "graph-1d", "index": ALL}, "extendData"),
    Input("sensor-data-buffer", "data"),
    [
        State({"type": "graph-1d-dropdown", "index": ALL}, "value"),
        State("graph-axes", "data"),
        State({"type": "graph-1d", "index": ALL}, "figure"),
    ],
)
def update_graph_1d(sensor_data, y_axis_list, graph_axes, current_figs):

    # # may need this later with multiple plots but I think it will still loop through drop downs
    # if "graph-1d" not in graph_axes:
    #     return dash.no_update

    # axes = graph_axes["graph-1d"]# = {"x-axis": "time", "y-axis": y_axis}
    try:
        figs = []
        if sensor_data:
            print(f"sensor_data: {sensor_data}")
            for y_axis in y_axis_list:
                if (
                    "time" not in sensor_data["variables"]
                    or y_axis not in sensor_data["variables"]
                ):
                    return dash.no_update

                x = [sensor_data["variables"]["time"]["data"]]
                y = [sensor_data["variables"][y_axis]["data"]]
                print(f"update: {[x]}, {[y]}")
                figs.append({"x": [x], "y": [y]})
            # return {"x": [x], "y": [y]}
            return figs

    except Exception as e:
        print(f"data update error: {e}")
        # return dash.no_update
        # return dash.no_update
    raise PreventUpdate
    # return dash.no_update


@callback(
    # Output({"type": "graph-2d-heatmap", "index": ALL}, "extendData"),
    Output({"type": "graph-2d-heatmap", "index": ALL}, "figure", allow_duplicate=True),
    Input("sensor-data-buffer", "data"),
    [
        State({"type": "graph-2d-dropdown", "index": ALL}, "value"),
        State("graph-axes", "data"),
        State("sensor-definition", "data"),
        State({"type": "graph-2d-heatmap", "index": ALL}, "figure"),
        State({"type": "graph-2d-heatmap", "index": ALL}, "id"),
    ],
    prevent_initial_call=True,
)
def update_graph_2d_heatmap(
    sensor_data, z_axis_list, graph_axes, sensor_definition, current_figs, graph_ids
):

    # # may need this later with multiple plots but I think it will still loop through drop downs
    # if "graph-1d" not in graph_axes:
    #     return dash.no_update

    # axes = graph_axes["graph-1d"]# = {"x-axis": "time", "y-axis": y_axis}
    try:
        heatmaps = []
        if sensor_data:
            print(f"update_2d_heatmap: {z_axis_list}, {graph_ids}")
            for z_axis, graph_id, current_fig in zip(
                z_axis_list, graph_ids, current_figs
            ):
                y_axis = graph_id["index"].split("::")[1]
                print(f"y_axis, z_axis: {y_axis}, {z_axis}")
                if (
                    "time" not in sensor_data["variables"]
                    or y_axis not in sensor_data["variables"]
                    or z_axis not in sensor_data["variables"]
                ):
                    raise PreventUpdate
                    # heatmaps.append(dash.no_update)
                    # # scatters.append(dash.no_update)
                    # continue
                    # return dash.no_update

                x = sensor_data["variables"]["time"]["data"]
                # print(f"current x, z: {x}, {current_fig['data'][0]['x']}, {current_fig['data'][0]['z']}")
                # print(f"current x, y, z: {x}, {len(current_fig['data'][0]['x'])}, {len(current_fig['data'][0]['y'])}, {len(current_fig['data'][0]['z'])}")
                # print(f"current x, y, z: {x}, {current_fig['data'][0]['x']}, {current_fig['data'][0]['y']}, {current_fig['data'][0]['z']}")

                # print(f"current fig: {current_fig}")

                if x in current_fig["data"][0]["x"]:
                    print("don't update")
                    raise PreventUpdate

                print("start x,y,z")
                if not isinstance(x, list):
                    x = [x]
                print(f"x: {x}")

                # work around until extendData works
                new_x = current_fig["data"][0]["x"]
                for nx in x:
                    current_fig["data"][0]["x"].append(nx)
                print(f"new x: {new_x}")
                y = current_fig["data"][0]["y"]
                if len(y) == 0:
                    y = sensor_data["variables"][y_axis]["data"]
                if not isinstance(y, list):
                    y = [y]
                print(f"y: {y}")
                orig_z = sensor_data["variables"][z_axis]["data"]
                if not isinstance(orig_z, list):
                    orig_z = [orig_z]
                print(f"update: {[x]}, {[y]}, {[orig_z]}")

                # work around until extendData works
                z = []
                new_z = current_fig["data"][0]["z"]
                if len(x) > 1:
                    for yi, yval in enumerate(y):
                        z.append([])
                        new_z = []
                        for xi, xval in enumerate(x):
                            new_z.append(orig_z[xi][yi])
                        z.append(new_z)
                else:
                    for yi, yval in enumerate(y):
                        current_fig["data"][0]["z"][yi].append(orig_z[yi])
                        # z.append([])
                        # new_z = []
                        # for xi, xval in enumerate(x):
                        #     new_z.append(orig_z[xi][yi])
                        z.append([orig_z[yi]])

                units = ""
                try:
                    y_units = f'({sensor_definition["variables"][y_axis]["attributes"]["units"]["data"]})'
                    z_units = f'({sensor_definition["variables"][z_axis]["attributes"]["units"]["data"]})'
                except KeyError:
                    pass

                # patched_heatmap = Patch()
                # print(f"patched heatmap: {patched_heatmap}")
                # if x not in patched_heatmap["data"][0]["x"]:
                #     patched_heatmap["data"][0]["x"].append(x)
                #     patched_heatmap["data"][0]["z"].append(z)

                print(f'change data: "x": {[x]}, "y": {[y]}, "z": {[z]}')
                # heatmaps.append({"x": [x], "y": [y], "z": [[z]]})
                # heatmaps.append({"x": [x], "y": [y], "z": [z]})

                # if len(current_fig["data"][0]["y"]) == 0:
                #     heatmaps.append({"x": [x], "y": [y], "z": [[z]]})
                # else:
                #     heatmaps.append({"x": [x], "z": [[z]]})

                # heatmaps.append({"data": [{"x": new_x, "y": y, "z": new_z}]})

                # heatmaps.append(patched_heatmap)
                heatmaps.append(current_fig)
                # new_fig = go.Figure(
                #     data=go.Heatmap(x=new_x, y=y, z=new_z, type="heatmap"),
                #     layout={
                #         "xaxis": {"title": f"{y_axis} {y_units}"},
                #         "yaxis": {"title": f"{z_axis} {z_units}"},
                #         # "yaxis": {"title": f"{y_axis} {y_units}"},
                #         # "colorscale": "rainbow"
                #     }
                # )

                # heatmaps.append(
                # )
            # return {"x": [x], "y": [y]}
            print(f"heatmaps: {heatmaps}")
            if len(heatmaps) == 0:
                raise PreventUpdate
            return heatmaps

    except Exception as e:
        print(f"heatmap update error: {e}")
        # return dash.no_update
        # return dash.no_update
    raise PreventUpdate
    # return dash.no_update


@callback(
    Output({"type": "graph-2d-line", "index": ALL}, "figure"),
    Input("sensor-data-buffer", "data"),
    [
        State({"type": "graph-2d-dropdown", "index": ALL}, "value"),
        State("graph-axes", "data"),
        State("sensor-definition", "data"),
        State({"type": "graph-2d-line", "index": ALL}, "figure"),
        State({"type": "graph-2d-line", "index": ALL}, "id"),
    ],
    prevent_initial_call=True,
)
def update_graph_2d_scatter(
    sensor_data, z_axis_list, graph_axes, sensor_definition, current_figs, graph_ids
):

    # # may need this later with multiple plots but I think it will still loop through drop downs
    # if "graph-1d" not in graph_axes:
    #     return dash.no_update

    # axes = graph_axes["graph-1d"]# = {"x-axis": "time", "y-axis": y_axis}
    try:
        # heatmaps = []
        scatters = []
        if sensor_data:
            print(f"sensor_data: {sensor_data}")
            for z_axis, graph_id, current_fig in zip(
                z_axis_list, graph_ids, current_figs
            ):
                y_axis = graph_id["index"].split("::")[1]
                if (
                    "time" not in sensor_data["variables"]
                    or y_axis not in sensor_data["variables"]
                    or z_axis not in sensor_data["variables"]
                ):
                    raise PreventUpdate
                    # heatmaps.append(dash.no_update)
                    # scatters.append(dash.no_update)
                    # continue
                    # return dash.no_update

                x = sensor_data["variables"]["time"]["data"]
                y = sensor_data["variables"][y_axis]["data"]
                z = sensor_data["variables"][z_axis]["data"]
                print(f"scatter update: {x}, {y}, {z}")

                # units = ""
                # try:
                #     y_units = f'({sensor_definition["variables"][y_axis]["attributes"]["units"]["data"]})'
                #     z_units = f'({sensor_definition["variables"][z_axis]["attributes"]["units"]["data"]})'
                # except KeyError:
                #     pass

                # patched_scatter = Patch()
                # patched_scatter["data"][0]["x"] = y
                # patched_scatter["data"][0]["y"] = z
                # patched_scatter["layout"]["title"] = str(x[-1])
                # heatmaps.append({"x": [x], "y": [y], "z": [z]})

                current_fig["data"][0]["x"] = y
                current_fig["data"][0]["y"] = z
                if isinstance(x, list):
                    x = x[-1]
                current_fig["layout"]["title"] = str(x)
                print(f"scatter current_fig: {current_fig}")
                scatters.append(current_fig)
                # scatters.append(
                #     go.Figure(
                #         data=go.Scatter(x=y, y=z, type="scatter"),
                #         layout={
                #             "xaxis": {"title": f"{y_axis} {y_units}"},
                #             "yaxis": {"title": f"{z_axis} {z_units}"},
                #             "title": str(x[-1])
                #             # "yaxis": {"title": f"{y_axis} {y_units}"},
                #             # "colorscale": "rainbow"
                #         }
                #     )
                # )
                # scatters.append(patched_scatter)

            # return {"x": [x], "y": [y]}

            return scatters

    except Exception as e:
        print(f"scatter update error: {e}")
        # return dash.no_update
        # return dash.no_update
    raise PreventUpdate
    # return dash.no_update


@callback(
    Output(
        {"type": "data-table-1d", "index": ALL}, "rowData"
    ),  # , Output("active-sensor-changes", "data")],
    Input("sensor-data-buffer", "data"),
    # Input("ws-sensor-instance", "message"),
    [
        State({"type": "data-table-1d", "index": ALL}, "rowData"),
        State({"type": "data-table-1d", "index": ALL}, "columnDefs"),
    ],  # , dcc.Store("sensor-definition", "data")],
    # prevent_initial_call=True,
)
def update_table_1d(sensor_data, row_data_list, col_defs_list):  # , sensor_definition):
    # sensor_def_data_changes = []
    # active_sensor_data_changes = []
    # # print(f"message data: {e}")
    # print(f"sensor_def_data: {sensor_def_data}")
    # print(f"row_data: {type(row_data)}, {row_data}, col_defs: {col_defs}")
    # if e is not None and "data" in e:
    if sensor_data:
        new_row_data_list = []
        try:
            # sensor_data = json.loads(e["data"])
            for row_data, col_defs in zip(row_data_list, col_defs_list):
                data = {}
                # print(f"row, col: {row_data}, {col_defs}")
                for col in col_defs:
                    name = col["field"]
                    # print(f"name: {name}")
                    if name in sensor_data["variables"]:
                        # print(f"variable: {msg["variables"][name]["data"]}")
                        data[name] = sensor_data["variables"][name]["data"]
                        # print(f"data: {data}")
                    else:
                        data[name] = ""
                # if row_data is None:
                #     row_data = []
                # print(f"row_data1: {type(row_data), {row_data}}")
                row_data.insert(0, data)
                # print(f"row_data2: {type(row_data), {row_data}}")
                # row_data = row_data.append(data)
                # test_row_data = []
                # test_row_data.append(data)
                # print(f"row-data: {test_row_data}")

                # limit size of table to 30 rows
                if len(row_data) > 30:
                    # return row_data[:30]
                    new_row_data_list.append(row_data[:30])
                else:
                    # return row_data
                    new_row_data_list.append(row_data)
                # return dash.no_update
            # row_data_list.append(row_data)
            # print(f"row_data_list: {row_data_list}")
            if len(new_row_data_list) == 0:
                raise PreventUpdate
            return new_row_data_list

        except Exception as e:
            print(f"data update error: {e}")
            # return dash.no_update
        raise PreventUpdate
        # return [dash.no_update for i in range(0,len(col_defs_list))]
        # return row_data
    else:
        # return dash.no_update
        raise PreventUpdate
        # return [dash.no_update for i in range(0,len(col_defs_list))]
        # return dash.no_update


@callback(
    Output(
        {"type": "data-table-2d", "index": ALL}, "rowData"
    ),  # , Output("active-sensor-changes", "data")],
    Input("sensor-data-buffer", "data"),
    # Input("ws-sensor-instance", "message"),
    [
        State({"type": "data-table-2d", "index": ALL}, "rowData"),
        State({"type": "data-table-2d", "index": ALL}, "columnDefs"),
    ],  # , dcc.Store("sensor-definition", "data")],
    # prevent_initial_call=True,
)
def update_table_2d(sensor_data, row_data_list, col_defs_list):  # , sensor_definition):
    # sensor_def_data_changes = []
    # active_sensor_data_changes = []
    # # print(f"message data: {e}")
    # print(f"sensor_def_data: {sensor_def_data}")
    # print(f"row_data: {type(row_data)}, {row_data}, col_defs: {col_defs}")
    # if e is not None and "data" in e:
    if sensor_data:
        new_row_data_list = []
        try:
            for col_defs in col_defs_list:
                dim_2d = col_defs[0]["field"]
                # row_data = [{}]*len(sensor_data["variables"][dim_2d]["data"])
                row_data = []
                for index in range(0, len(sensor_data["variables"][dim_2d]["data"])):
                    data = {}
                    for col in col_defs:
                        name = col["field"]
                        data[name] = sensor_data["variables"][name]["data"][index]
                        # print(f"row_data: {index} {name} : {row_data[index][name]} : {row_data[index]}")
                    # print(f"row_data: {row_data}")
                    # print(f"data: {data}")
                    row_data.append(data)
                # print(f"row_data: {row_data}")
                new_row_data_list.append(row_data)
            # print(f"new_row_data_list: {new_row_data_list}")
            return new_row_data_list

            # # sensor_data = json.loads(e["data"])
            # for row_data, col_defs in zip(row_data_list,col_defs_list):
            #     # dim_2d = table_id.split("::")[1]
            #     data = {}
            #     # print(f"row, col: {row_data}, {col_defs}")
            #     for col in col_defs:
            #         name = col["field"]
            #         # print(f"name: {name}")
            #         if name in sensor_data["variables"]:
            #             # print(f"variable: {msg["variables"][name]["data"]}")
            #             data[name] = sensor_data["variables"][name]["data"]
            #             # print(f"data: {data}")
            #         else:
            #             data[name] = ""
            #     # if row_data is None:
            #     #     row_data = []
            #     # print(f"row_data1: {type(row_data), {row_data}}")

            #     for i in range(0, len(data[col_defs[0]["field"]])):

            #     row_data.insert(0, data)
            #     # print(f"row_data2: {type(row_data), {row_data}}")
            #     # row_data = row_data.append(data)
            #     # test_row_data = []
            #     # test_row_data.append(data)
            #     # print(f"row-data: {test_row_data}")

            #     # limit size of table to 30 rows
            #     if len(row_data) > 30:
            #         # return row_data[:30]
            #         new_row_data_list.append(row_data[:30])
            #     else:
            #         # return row_data
            #         new_row_data_list.append(row_data)
            #     # return dash.no_update
            # # row_data_list.append(row_data)
            # # print(f"row_data_list: {row_data_list}")
            # if len(new_row_data_list) == 0:
            #     raise PreventUpdate
            # return new_row_data_list

        except Exception as e:
            print(f"data update error: {e}")
            # return dash.no_update
        raise PreventUpdate
        # return [dash.no_update for i in range(0,len(col_defs_list))]
        # return row_data
    else:
        # return dash.no_update
        raise PreventUpdate
        # return [dash.no_update for i in range(0,len(col_defs_list))]
        # return dash.no_update


#    content = dbc.Row(children=[

#         dbc.Label("z-axis min:"),
#         dbc.Col(dbc.Input(type="number", id={"type": "graph-2d-z-axis-min", "index": f"{xaxis}::{yaxis}"})),
#         dbc.Label("z-axis max:"),
#         dbc.Col(dbc.Input(type="number", id={"type": "graph-2d-z-axis-max", "index": f"{xaxis}::{yaxis}"})),
#     ])

#     axes_collapse = html.Div(
#         [

#             dbc.Button(
#                 "Axes Settings",
#                 id={"type": "graph-2d-axes-settings", "index": f"{xaxis}::{yaxis}"},
#                 className="mb-3",
#                 # color="primary",
#                 n_clicks=0,
#             ),
#             dbc.Collapse(
#                 dbc.Card(dbc.CardBody(childern=[content])),
#                 id={"type": "graph-2d-axes-collapse", "index": f"{xaxis}::{yaxis}"},
#                 is_open=False,
#             ),
#         ]
#     )


@callback(
    Output(
        {"type": "graph-2d-heatmap", "index": MATCH}, "figure", allow_duplicate=True
    ),
    [Input({"type": "graph-2d-z-axis-submit", "index": MATCH}, "n_clicks")],
    [
        State({"type": "graph-2d-z-axis-min", "index": MATCH}, "value"),
        State({"type": "graph-2d-z-axis-max", "index": MATCH}, "value"),
        State({"type": "graph-2d-heatmap", "index": MATCH}, "figure"),
    ],
    prevent_initial_call=True,
)
def set_2d_z_axis_range(n, axis_min, axis_max, heatmap):

    print(f"z-axis range: min={axis_min}, max={axis_max}")
    fig = go.Figure(heatmap)
    fig = fig.update_layout(coloraxis=dict(cauto=False, cmax=axis_max, cmin=axis_min))
    print(f"update fig: {fig}")
    # try:
    #     heatmap['layout']['template']['layout']['coloraxis']['cmin'] = axis_min
    #     heatmap['layout']['template']['layout']['coloraxis']['cmix'] = axis_max
    #     print(f"heatmap: {heatmap['layout']['template']['layout']['coloraxis']}") 
    #     # for k,v in heatmap['layout']["template"]['coloraxis'].items():
    #     #     print(f"[{k}]: [{v.keys()}]")
    # except KeyError:
    #     pass
    # # heatmap.update_layout(coloraxis=dict(cmax=axis_max, cmin=axis_min))

    return fig


# @callback(
#     Output(
#         {"type": "graph-2d-heatmap", "index": MATCH}, "figure", allow_duplicate=True
#     ),
#     [Input({"type": "graph-2d-z-axis-max", "index": MATCH}, "value")],
#     [
#         State({"type": "graph-2d-heatmap", "index": MATCH}, "figure"),
#         State({"type": "graph-2d-z-axis-min", "index": MATCH}, "value"),
#     ],
#     prevent_initial_call=True,
# )
# def set_2d_z_axis_max(axis_max, heatmap, axis_min):

#     print(f"z-axis range: min={axis_min}, max={axis_max}")
#     heatmap.update_layout(coloraxis=dict(cmax=axis_max, cmin=axis_min))

#     return heatmap


@callback(
    Output("ws-sensor-instance", "send"), Input("ws-send-instance-buffer", "children")
)
def send_to_instance(value):
    print(f"sending: {value}")
    return value
