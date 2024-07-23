from datetime import datetime, timezone
import json
import dash
from dash import html, callback, dcc, Input, Output, dash_table, State
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
from pydantic import BaseSettings
from ulid import ULID
import dash_ag_grid as dag
import pandas as pd
# import pymongo

dash.register_page(
    __name__,
    path="/sensor-registry",
    title="UAS-DAQ Sensor Registry",  # , prevent_initial_callbacks=True
)

from envds.daq.db import (
    SensorTypeRegistration,
    SensorRegistration,
    # init_db_models,
    # register_sensor_type,
    # register_sensor,
    # get_sensor_type_registration,
    # get_sensor_registration,
    get_all_sensor_registration,
    # get_sensor_registration_by_pk,
    get_all_sensor_type_registration,
    # get_sensor_type_registration_by_pk,
)

#TODO Make DBClient generic enough to use redis

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
#             db = self.client[database]
#             db_collection = db[collection]
#             result = db_collection.find_one(query)
#             if result:
#                 update = {"last_update": datetime.now(tz=timezone.utc)}
#                 db_data_client.update_one(database, collection, result, update)
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


ws_send_buffer = html.Div(id="ws-send-buffer", style={"display": "none"})

def get_layout():
    # print("here:1")
    layout = html.Div(
        [
            html.H1("Sensor Registry"),
            # get_button,
            dbc.Accordion(
                [
                    dbc.AccordionItem(
                        [
                            dag.AgGrid(
                                id="sensor-defs-table",
                                rowData=[],
                                columnDefs=[
                                    {
                                        "field": "make",
                                        "headerName": "Make/Mfg",
                                        "filter": True,
                                    },
                                    {
                                        "field": "model",
                                        "headerName": "Model",
                                        "filter": True,
                                    },
                                    {
                                        "field": "version",
                                        "headerName": "Format Version",
                                        "filter": True,
                                    },
                                ],
                            )
                        ],
                        title="Sensor Definitions",
                    ),
                    dbc.AccordionItem(
                        [
                            dag.AgGrid(
                                id="active-sensor-table",
                                rowData=[],
                                columnDefs=[
                                    {
                                        "field": "sensor_id",
                                        "headerName": "Sensor ID",
                                        "filter": True,
                                        "cellRenderer": "markdown",
                                    },
                                    {
                                        "field": "make",
                                        "headerName": "Make/Mfg",
                                        "filter": True,
                                    },
                                    {
                                        "field": "model",
                                        "headerName": "Model",
                                        "filter": True,
                                    },
                                    {
                                        "field": "serial_number",
                                        "headerName": "Serial Number",
                                        "filter": True,
                                    },
                                    {
                                        "field": "sampling_sytem_id",
                                        "headerName": "Sampling System ID",
                                        "filter": True,
                                        "cellRenderer": "markdown",
                                    },
                                ],
                            )
                        ],
                        title="Active Sensors",
                    ),
                ],
                id="sensor-accordion",
            ),
            WebSocket(
                id="ws-sensor-registry",
                url=f"ws://10.55.169.1:8080/envds/dashboard/ws/sensor-registry/main",
            ),
            ws_send_buffer,
            dcc.Store(id="sensor-defs-changes", data=[]),
            dcc.Store(id="active-sensor-changes", data=[]),
            # dcc.Interval(id="test-interval", interval=(10*1000)),
            dcc.Interval(
                id="table-update-interval", interval=(5 * 1000), n_intervals=0
            ),
            # dcc.Interval(id="active-sensor-update-interval", interval=(5*1000), n_intervals=0),
            # html.Div(id="test-output")
        ]
    )
    # print("here:2")

    request = {"client-request": "start-updates"}
    # print("here:3")
    # print(f"sent request: {request}")
    ws_send_buffer.children = json.dumps(request)
    # print("here:4")
    # websocket.send("test programatically")
    return layout


layout = get_layout  # ()



@callback(
    Output("sensor-defs-table", "rowData"),
    Input("table-update-interval", "n_intervals"),
    State("sensor-defs-table", "rowData")
    # prevent_initial_call=True
)
def update_sensor_definitions(count, table_data):
    # print(f"sensor_def: {count}")
    update = False
    new_data = []
    try:
        # db_registry_client.connect()
        # if db_registry_client:
        #     sensor_def_registry = db_registry_client.get_collection(
        #         "registry", "sensor_definition"
        #     )
        reg_list = get_all_sensor_type_registration()
        for doc in get_all_sensor_type_registration():
            if doc is not None:
                # print(f"doc: {doc}")
                # id = doc["_id"]
                make = doc["make"]
                model = doc["model"]
                version = doc["version"]
                id = doc.source_id
                make = doc.make
                model = doc.model
                version = "v1.0.0" # this will need to be updated in the def

                sensor_def = {
                    "sensor-def-id": id,
                    "make": make,
                    "model": model,
                    "version": version,
                }
                if sensor_def not in table_data:
                    table_data.append(sensor_def)
                    update = True
                new_data.append(sensor_def)

            remove_data = []
            for index, data in enumerate(table_data):
                if data not in new_data:
                    update = True
                    remove_data.insert(0, index)
            for index in remove_data:
                table_data.pop(index)

            if update:
                return table_data
            else:
                return dash.no_update

    except Exception as e:
        print(f"update_sensor_definitions error: {e}")
        return dash.no_update


@callback(
    Output("active-sensor-table", "rowData"),
    Input("table-update-interval", "n_intervals"),
    State("active-sensor-table", "rowData")
)
def update_active_sensors(count, table_data):

    # print(f"active_sensor: {count}")
    update = False
    new_data = []
    try:
        # db_registry_client.connect()
        # if db_registry_client:
        #     # print(db_registry_client)
        #     sensor_registry = db_registry_client.get_collection("registry", "sensor")
        #     # print(sensor_registry)
        #     for doc in sensor_registry.find():
        for doc in get_all_sensor_registration():
            if doc is not None:
                # print(f"doc: {doc}")
                # make = doc["make"]
                # model = doc["model"]
                # serial_number = doc["serial_number"]
                # version = doc["version"]
                make = doc.make
                model = doc.model
                serial_number = doc.serial_number
                version = "v1.0.0"
                sensor_id = "::".join([make, model, serial_number])
                sampling_system_id = "unknown::unknown::unknown"

                sensor = {
                    "sensor_id": f"[{sensor_id}](http://10.55.169.1:8080/envds/dashboard/dash/sensor/{sensor_id})",
                    "make": make,
                    "model": model,
                    "serial_number": serial_number,
                    "sampling_system_id": f"[{sampling_system_id}](http://10.55.169.1:8080/envds/dashboard/dash/sampling-system/{sampling_system_id})",
                }
                if sensor not in table_data:
                    table_data.append(sensor)
                    update = True
                new_data.append(sensor)

            remove_data = []
            for index, data in enumerate(table_data):
                if data not in new_data:
                    update = True
                    remove_data.insert(0, index)
            for index in remove_data:
                table_data.pop(index)

            if update:
                return table_data
            else:
                return dash.no_update

    except Exception as e:
        print(f"update_active_sensors error: {e}")
        return dash.no_update


# @callback(
#     [Output("sensor-defs-changes", "data"), Output("active-sensor-changes", "data")],
#     Input("ws-sensor-registry", "message"),
#     [State("sensor-defs-table", "rowData"), State("active-sensor-table", "rowData")],
#     prevent_initial_call=True,
# )
# def sensor_registry_message(e, sensor_def_data, active_sensor_data):
#     sensor_def_data_changes = []
#     active_sensor_data_changes = []
#     # print(f"message data: {e}")
#     print(f"sensor_def_data: {sensor_def_data}")
#     if e is not None and "data" in e:
#         try:
#             msg = json.loads(e["data"])
#             # print(f"message: {msg}")
#             # {'database': 'registry', 'collection': 'sensor_definition', 'operation-type': 'insert', 'data': {'_id':
#             if (
#                 msg["database"] == "registry"
#                 and msg["collection"] == "sensor_definition"
#             ):

#                 op_type = msg["operation-type"]
#                 id = msg["data"]["_id"]
#                 make = msg["data"]["make"]
#                 model = msg["data"]["model"]
#                 version = msg["data"]["version"]

#                 msg_sensor_def = {
#                     "sensor-def-id": id,
#                     "make": make,
#                     "model": model,
#                     "version": version,
#                 }

#                 new_data = True
#                 for index, sensor_def in enumerate(sensor_def_data):
#                     print(f"{index}: {sensor_def} -- {sensor_def_data}")
#                     if "sensor-def-id" not in sensor_def_data:
#                         break

#                     if sensor_def["sensor-def-id"] == id:
#                         sensor_def_data_changes.append(
#                             {
#                                 "operation": op_type,
#                                 "index": index,
#                                 "data": msg_sensor_def,
#                             }
#                         )
#                         new_data = False
#                         break
#                 if new_data and op_type in ["insert", "update", "replace"]:
#                     sensor_def_data_changes.append(
#                         {"operation": op_type, "index": -1, "data": msg_sensor_def}
#                     )
#                     # if op_type == "delete":
#                     #     sensor_def_data.remove(sensor_def)
#                     # elif op_type == "replace":
#                     #     sensor_def = {
#                     #         "sensor-def-id": id,
#                     #         "make": make,
#                     #         "model": model,
#                     #         "version": version,
#                     #     }
#                     # update = False
#                     # break
#                 # if update:
#                 #     # print(f"op_type: {op_type}")
#                 #     if op_type in ["insert", "update", "replace"]:
#                 #         # print(f"op_type: {op_type}, {id}")
#                 #         sensor_def_data.append(
#                 #             {
#                 #                 "sensor-def-id": id,
#                 #                 "make": make,
#                 #                 "model": model,
#                 #                 "version": version,
#                 #             }
#                 #         )

#             elif (
#                 msg["database"] == "registry"
#                 and msg["collection"] == "sensor"
#             ):

#                 op_type = msg["operation-type"]
#                 # print(f"***sensor:op-type: {op_type}, {msg}")
#                 # # id = msg["data"]["_id"]
#                 make = msg["data"]["make"]
#                 model = msg["data"]["model"]
#                 serial_number = msg["data"]["serial_number"]
#                 version = msg["data"]["version"]
#                 id = "::".join([make,model,serial_number])
#                 sampling_system = "unknown"

#                 msg_sensor = {
#                     "sensor-id": id,
#                     "make": make,
#                     "model": model,
#                     "serial_number": serial_number,
#                     "sampling_system": sampling_system
#                 }

#                 new_data = True
#                 for index, sensor in enumerate(active_sensor_data):
#                     print(f"{index}: {sensor} -- {active_sensor_data}")
#                     if "sensor-id" not in active_sensor_data:
#                         break

#                     if sensor_def["sensor-id"] == id:
#                         active_sensor_data_changes.append(
#                             {
#                                 "operation": op_type,
#                                 "index": index,
#                                 "data": msg_sensor,
#                             }
#                         )
#                         new_data = False
#                         break
#                 if new_data and op_type in ["insert", "update", "replace"]:
#                     active_sensor_data_changes.append(
#                         {"operation": op_type, "index": -1, "data": msg_sensor}
#                     )
#                     # if op_type == "delete":
#                     #     sensor_def_data.remove(sensor_def)
#                     # elif op_type == "replace":
#                     #     sensor_def = {
#                     #         "sensor-def-id": id,
#                     #         "make": make,
#                     #         "model": model,
#                     #         "version": version,
#                     #     }
#                     # update = False
#                     # break
#                 # if update:
#                 #     # print(f"op_type: {op_type}")
#                 #     if op_type in ["insert", "update", "replace"]:
#                 #         # print(f"op_type: {op_type}, {id}")
#                 #         sensor_def_data.append(
#                 #             {
#                 #                 "sensor-def-id": id,
#                 #                 "make": make,
#                 #                 "model": model,
#                 #                 "version": version,
#                 #             }
#                 #         )


#             # elif msg["database"] == "registry" and msg["collection"] == "sensor":

#             #     op_type = msg["operation-type"]
#             #     print(f"***sensor:op-type: {op_type}, {msg}")
#             #     # id = msg["data"]["_id"]
#             #     make = msg["data"]["make"]
#             #     model = msg["data"]["model"]
#             #     serial_number = msg["data"]["serial_number"]
#             #     version = msg["data"]["version"]
#             #     id = "::".join([make, model, serial_number])
#             #     sampling_system = "unknown"

#             #     msg_sensor = {
#             #         "sensor-id": id,
#             #         "make": make,
#             #         "model": model,
#             #         "serial_number": serial_number,
#             #         "sampling_system": sampling_system,
#             #     }

#             #     new_data = True
#             #     for index, sensor in enumerate(active_sensor_data):
#             #         if sensor["sensorid"] == id:
#             #             active_sensor_data_changes.append(
#             #                 {"operation": op_type, "index": index, "data": msg_sensor}
#             #             )
#             #             new_data = False
#             #             break
#             #     if new_data and op_type in ["insert", "update", "replace"]:
#             #         active_sensor_data_changes.append(
#             #             {"operation": "insert", "data": msg_sensor}
#             #         )

#             #     # update = True
#             #     # for sensor in active_sensor_data:
#             #     #     # if sensor["make"] == make and sensor["model"] == model and sensor["serial_number"] == serial_number:
#             #     #     if sensor["sensor-id"] == id:
#             #     #         if op_type == "delete":
#             #     #             active_sensor_data.remove(sensor)
#             #     #         elif op_type == "replace":
#             #     #             sensor = {
#             #     #                 "sensor-id": id,
#             #     #                 "make": make,
#             #     #                 "model": model,
#             #     #                 "serial_number": serial_number,
#             #     #                 "sampling_system": sampling_system
#             #     #             }
#             #     #         update = False
#             #     #         break
#             #     # if update:
#             #     #     # print(f"op_type: {op_type}")
#             #     #     if op_type in ["insert", "update", "replace"]:
#             #     #         # print(f"op_type: {op_type}, {id}")
#             #     #         active_sensor_data.append(
#             #     #             {
#             #     #                 "sensor-id": id,
#             #     #                 "make": make,
#             #     #                 "model": model,
#             #     #                 "serial_number": serial_number,
#             #     #                 "sampling_system": sampling_system
#             #     #             }
#             #     #         )
#             # print(sensor_def_data)
#             # return sensor_def_data, active_sensor_data
#         except (json.JSONDecodeError, KeyError, Exception) as e:
#             print(f"sensor_registry_message load error: {e}")

#     else:
#         print("not e")
#     print(f"changes: {sensor_def_data_changes}, {active_sensor_data_changes}")
#     return sensor_def_data_changes, active_sensor_data_changes


# @callback(
#     # [
#     #     Output("sensor-defs-table", "rowData"),
#     #     Output("sensor-defs-changes", "clear_data")
#     # ],
#     Output("sensor-defs-table", "rowData"),
#     Input("sensor-defs-changes", "data"),
#     State("sensor-defs-table", "rowData")
# )
# def update_sensor_defs_table(change_data, sensor_def_data):
#     # sensor_def_data = []
#     print(f"change_data: {change_data}")
#     if change_data is None or len(change_data) == 0:
#         return dash.no_update

#     update = False
#     for change in change_data:
#         try:
#             op_type = change["operation"]
#             index = change.get("index", -1)
#             print(f"change: {change}, op_type: {op_type}, index: {index}")
#             if op_type == "delete":
#                 sensor_def_data.remove(change["data"])
#                 update = True
#                 continue
#             elif op_type == "replace":
#                 if index >= 0:
#                     sensor_def_data[index] = change["data"]
#                     update = True
#                 else:
#                     sensor_def_data.append(change["data"])
#                 update = True
#                 continue
#             elif op_type in ["update", "insert"]:
#                 if index >= 0:
#                     # sensor_def_data[index] = change["data"]
#                     update = False
#                 else:
#                     sensor_def_data.append(change["data"])
#                     update = True
#                 continue
#             # elif op_type == "insert":
#             #     if index >= 0:
#             #         update = False
#             #     else:
#             #         sensor_def_data.append(change["data"])
#             #         update = True
#             #     continue

#         except (KeyError, TypeError, Exception):
#             continue

#     print(f"update table: {update}, {sensor_def_data}")
#     if update:
#         return sensor_def_data
#     else:
#         return dash.no_update

#         # if msg["database"] == "registry" and msg["collection"] == "sensor_definition":

#         #     op_type = msg["operation-type"]
#         #     id = msg["data"]["_id"]
#         #     make = msg["data"]["make"]
#         #     model = msg["data"]["model"]
#         #     version = msg["data"]["version"]

#         #     new_data = True
#         #     for sensor_def in sensor_def_data:

#         #         msg_sensor_def = {
#         #             "sensor-def-id": id,
#         #             "make": make,
#         #             "model": model,
#         #             "version": version,
#         #         }

#         #         if sensor_def["sensor-def-id"] == id:
#         #             sensor_def_data_changes.append({"operation": op_type, "data": msg_sensor_def})
#         #             new_data = False
#         #             break
#         #     if new_data and op_type in ["insert", "update", "replace"]:
#         #         sensor_def_data_changes.append({"operation": "insert", "data": msg_sensor_def})
#         #             # if op_type == "delete":
#         #             #     sensor_def_data.remove(sensor_def)
#         #             # elif op_type == "replace":
#         #             #     sensor_def = {
#         #             #         "sensor-def-id": id,
#         #             #         "make": make,
#         #             #         "model": model,
#         #             #         "version": version,
#         #             #     }
#         #             # update = False
#         #             # break
#         #     # if update:
#         #     #     # print(f"op_type: {op_type}")
#         #     #     if op_type in ["insert", "update", "replace"]:
#         #     #         # print(f"op_type: {op_type}, {id}")
#         #     #         sensor_def_data.append(
#         #     #             {
#         #     #                 "sensor-def-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "version": version,
#         #     #             }
#         #     #         )
#         # elif msg["database"] == "registry" and msg["collection"] == "sensor":

#         #     op_type = msg["operation-type"]
#         #     print(f"***sensor:op-type: {op_type}, {msg}")
#         #     # id = msg["data"]["_id"]
#         #     make = msg["data"]["make"]
#         #     model = msg["data"]["model"]
#         #     serial_number = msg["data"]["serial_number"]
#         #     version = msg["data"]["version"]
#         #     id = "::".join([make,model,serial_number])
#         #     sampling_system = "unknown"

#         #     msg_sensor = {
#         #         "sensor-id": id,
#         #         "make": make,
#         #         "model": model,
#         #         "serial_number": serial_number,
#         #         "sampling_system": sampling_system
#         #     }

#         #     new_data = True
#         #     for sensor in active_sensor_data:
#         #         if sensor["sensorid"] == id:
#         #             active_sensor_data_changes.append({"operation": op_type, "data": msg_sensor})
#         #             new_data = False
#         #             break
#         #     if new_data and op_type in ["insert", "update", "replace"]:
#         #         active_sensor_data_changes.append({"operation": "insert", "data": msg_sensor})

#         #     # update = True
#         #     # for sensor in active_sensor_data:
#         #     #     # if sensor["make"] == make and sensor["model"] == model and sensor["serial_number"] == serial_number:
#         #     #     if sensor["sensor-id"] == id:
#         #     #         if op_type == "delete":
#         #     #             active_sensor_data.remove(sensor)
#         #     #         elif op_type == "replace":
#         #     #             sensor = {
#         #     #                 "sensor-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "serial_number": serial_number,
#         #     #                 "sampling_system": sampling_system
#         #     #             }
#         #     #         update = False
#         #     #         break
#         #     # if update:
#         #     #     # print(f"op_type: {op_type}")
#         #     #     if op_type in ["insert", "update", "replace"]:
#         #     #         # print(f"op_type: {op_type}, {id}")
#         #     #         active_sensor_data.append(
#         #     #             {
#         #     #                 "sensor-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "serial_number": serial_number,
#         #     #                 "sampling_system": sampling_system
#         #     #             }
#         #     #         )

# @callback(
#     # [
#     #     Output("sensor-defs-table", "rowData"),
#     #     Output("sensor-defs-changes", "clear_data")
#     # ],
#     Output("active-sensor-table", "rowData"),
#     Input("active-sensor-changes", "data"),
#     State("active-sensor-table", "rowData")
# )
# def update_active_sensor_table(change_data, active_sensor_data):
#     # sensor_def_data = []
#     print(f"change_data: {change_data}")
#     if change_data is None or len(change_data) == 0:
#         return dash.no_update

#     # TODO: refactor code to check for existence in this callback to avoid
#     #       multiple entries

#     update = False
#     for change in change_data:
#         try:
#             op_type = change["operation"]
#             index = change.get("index", -1)
#             print(f"change: {change}, op_type: {op_type}, index: {index}")
#             if op_type == "delete":
#                 active_sensor_data.remove(change["data"])
#                 update = True
#                 continue
#             elif op_type == "replace":
#                 if index >= 0:
#                     active_sensor_data[index] = change["data"]
#                     update = True
#                 else:
#                     active_sensor_data.append(change["data"])
#                 update = True
#                 continue
#             elif op_type in ["update", "insert"]:
#                 if index >= 0:
#                     # sensor_def_data[index] = change["data"]
#                     update = False
#                 else:
#                     active_sensor_data.append(change["data"])
#                     update = True
#                 continue
#             # elif op_type == "insert":
#             #     if index >= 0:
#             #         update = False
#             #     else:
#             #         sensor_def_data.append(change["data"])
#             #         update = True
#             #     continue

#         except (KeyError, TypeError, Exception):
#             continue

#     print(f"update table: {update}, {active_sensor_data}")
#     if update:
#         return active_sensor_data
#     else:
#         return dash.no_update

#         # if msg["database"] == "registry" and msg["collection"] == "sensor_definition":

#         #     op_type = msg["operation-type"]
#         #     id = msg["data"]["_id"]
#         #     make = msg["data"]["make"]
#         #     model = msg["data"]["model"]
#         #     version = msg["data"]["version"]

#         #     new_data = True
#         #     for sensor_def in sensor_def_data:

#         #         msg_sensor_def = {
#         #             "sensor-def-id": id,
#         #             "make": make,
#         #             "model": model,
#         #             "version": version,
#         #         }

#         #         if sensor_def["sensor-def-id"] == id:
#         #             sensor_def_data_changes.append({"operation": op_type, "data": msg_sensor_def})
#         #             new_data = False
#         #             break
#         #     if new_data and op_type in ["insert", "update", "replace"]:
#         #         sensor_def_data_changes.append({"operation": "insert", "data": msg_sensor_def})
#         #             # if op_type == "delete":
#         #             #     sensor_def_data.remove(sensor_def)
#         #             # elif op_type == "replace":
#         #             #     sensor_def = {
#         #             #         "sensor-def-id": id,
#         #             #         "make": make,
#         #             #         "model": model,
#         #             #         "version": version,
#         #             #     }
#         #             # update = False
#         #             # break
#         #     # if update:
#         #     #     # print(f"op_type: {op_type}")
#         #     #     if op_type in ["insert", "update", "replace"]:
#         #     #         # print(f"op_type: {op_type}, {id}")
#         #     #         sensor_def_data.append(
#         #     #             {
#         #     #                 "sensor-def-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "version": version,
#         #     #             }
#         #     #         )
#         # elif msg["database"] == "registry" and msg["collection"] == "sensor":

#         #     op_type = msg["operation-type"]
#         #     print(f"***sensor:op-type: {op_type}, {msg}")
#         #     # id = msg["data"]["_id"]
#         #     make = msg["data"]["make"]
#         #     model = msg["data"]["model"]
#         #     serial_number = msg["data"]["serial_number"]
#         #     version = msg["data"]["version"]
#         #     id = "::".join([make,model,serial_number])
#         #     sampling_system = "unknown"

#         #     msg_sensor = {
#         #         "sensor-id": id,
#         #         "make": make,
#         #         "model": model,
#         #         "serial_number": serial_number,
#         #         "sampling_system": sampling_system
#         #     }

#         #     new_data = True
#         #     for sensor in active_sensor_data:
#         #         if sensor["sensorid"] == id:
#         #             active_sensor_data_changes.append({"operation": op_type, "data": msg_sensor})
#         #             new_data = False
#         #             break
#         #     if new_data and op_type in ["insert", "update", "replace"]:
#         #         active_sensor_data_changes.append({"operation": "insert", "data": msg_sensor})

#         #     # update = True
#         #     # for sensor in active_sensor_data:
#         #     #     # if sensor["make"] == make and sensor["model"] == model and sensor["serial_number"] == serial_number:
#         #     #     if sensor["sensor-id"] == id:
#         #     #         if op_type == "delete":
#         #     #             active_sensor_data.remove(sensor)
#         #     #         elif op_type == "replace":
#         #     #             sensor = {
#         #     #                 "sensor-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "serial_number": serial_number,
#         #     #                 "sampling_system": sampling_system
#         #     #             }
#         #     #         update = False
#         #     #         break
#         #     # if update:
#         #     #     # print(f"op_type: {op_type}")
#         #     #     if op_type in ["insert", "update", "replace"]:
#         #     #         # print(f"op_type: {op_type}, {id}")
#         #     #         active_sensor_data.append(
#         #     #             {
#         #     #                 "sensor-id": id,
#         #     #                 "make": make,
#         #     #                 "model": model,
#         #     #                 "serial_number": serial_number,
#         #     #                 "sampling_system": sampling_system
#         #     #             }
#         #     #         )

# @callback(
#     [Output("sensor-defs-table", "rowData"), Output("active-sensor-table", "rowData")],
#     # Output("sensor-defs-table", "rowData"),
#     [Input("ws-sensor", "message")]
# )
# def message(e):
#     # try:
#     #     print(f"message: {json.loads(e['data'])}")
#     # except Exception as e:
#     #     print(f"error: {e}")
#     # print(f"sensor_def_data: {sensor_def_data}")
#     print("sensor:message")
#     if e is not None and "data" in e:
#         try:
#             msg = json.loads(e['data'])
#             # print(f"message: {msg}")
#             # {'database': 'registry', 'collection': 'sensor_definition', 'operation-type': 'insert', 'data': {'_id':
#             if msg["database"] == "registry" and msg["collection"] == "sensor_definition":

#                 op_type = msg["operation-type"]
#                 id = msg["data"]["_id"]
#                 make = msg["data"]["make"]
#                 model = msg["data"]["model"]
#                 version = msg["data"]["version"]

#                 update = True
#                 for sensor_def in sensor_def_data:
#                     if sensor_def["sensor-def-id"] == id:
#                         if op_type == "delete":
#                             sensor_def_data.remove(sensor_def)
#                         elif op_type == "replace":
#                             sensor_def = {
#                                 "sensor-def-id": id,
#                                 "make": make,
#                                 "model": model,
#                                 "version": version,
#                             }
#                         update = False
#                         break
#                 if update:
#                     # print(f"op_type: {op_type}")
#                     if op_type in ["insert", "update", "replace"]:
#                         # print(f"op_type: {op_type}, {id}")
#                         sensor_def_data.append(
#                             {
#                                 "sensor-def-id": id,
#                                 "make": make,
#                                 "model": model,
#                                 "version": version,
#                             }
#                         )
#             elif msg["database"] == "registry" and msg["collection"] == "sensor":

#                 op_type = msg["operation-type"]
#                 print(f"***sensor:op-type: {op_type}, {msg}")
#                 # id = msg["data"]["_id"]
#                 make = msg["data"]["make"]
#                 model = msg["data"]["model"]
#                 serial_number = msg["data"]["serial_number"]
#                 version = msg["data"]["version"]
#                 id = "::".join([make,model,serial_number])
#                 sampling_system = "unknown"

#                 update = True
#                 for sensor in active_sensor_data:
#                     # if sensor["make"] == make and sensor["model"] == model and sensor["serial_number"] == serial_number:
#                     if sensor["sensor-id"] == id:
#                         if op_type == "delete":
#                             active_sensor_data.remove(sensor)
#                         elif op_type == "replace":
#                             sensor = {
#                                 "sensor-id": id,
#                                 "make": make,
#                                 "model": model,
#                                 "serial_number": serial_number,
#                                 "sampling_system": sampling_system
#                             }
#                         update = False
#                         break
#                 if update:
#                     # print(f"op_type: {op_type}")
#                     if op_type in ["insert", "update", "replace"]:
#                         # print(f"op_type: {op_type}, {id}")
#                         active_sensor_data.append(
#                             {
#                                 "sensor-id": id,
#                                 "make": make,
#                                 "model": model,
#                                 "serial_number": serial_number,
#                                 "sampling_system": sampling_system
#                             }
#                         )
#             # print(sensor_def_data)
#             # return sensor_def_data, active_sensor_data
#         except (json.JSONDecodeError, KeyError, Exception) as e:
#             print(f"active-sensor load error: {e}")

#     else:
#         print("not e")

#     return sensor_def_data, active_sensor_data


@callback(Output("ws-sensor-registry", "send"), Input("ws-send-buffer", "children"))
def send(value):
    print(f"sending: {value}")
    return value


# @callback(Output("ws-send-buffer", "children"), [Input("get-data-button", "n_clicks")])
# def get_data(n_clicks):
#     if n_clicks > 0:
#         request = {"client-request": "start-updates"}
#         # print("here:3")
#         print(f"sent request: {request}")
#         # ws_send_buffer.children = json.dumps(request)

#         return json.dumps(request)
#     return ""

# # startup code
# send("startup request")
