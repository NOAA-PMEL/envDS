import asyncio
import json
import logging
import math
from time import sleep

# import numpy as np
from ulid import ULID
from pathlib import Path
import os

import httpx
from logfmter import Logfmter

# from registry import registry
from flask import Flask, request
from pydantic import BaseSettings
from cloudevents.http import CloudEvent, from_http

# from cloudevents.http.conversion import from_http
from cloudevents.conversion import to_structured  # , from_http
from cloudevents.exceptions import InvalidStructuredJSON

from datetime import datetime, timezone
import pymongo

import dash
from dash import Dash, html, dcc, callback, Output, Input
import plotly.express as px
import pandas as pd
import uvicorn

handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)


# class Settings(BaseSettings):
#     host: str = '0.0.0.0'
#     port: int = 8787
#     debug: bool = False
#     url: str = 'https://localhost:8444/erddap/tabledap'
#     author: str = 'super_secret_author'
#     dry_run: bool = False

#     class Config:
#         env_prefix = 'IOT_ERDDAP_INSERT_'
#         case_sensitive = False

# uasdaq_user_password = os.environ.get("REGISTRAR_MONGODB_USER_PW")
# L.info("pw", extra={"pw": uasdaq_user_password})


class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    knative_broker: str = (
        "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default"
    )
    mongodb_user_name: str = ""
    mongodb_user_password: str = ""
    mongodb_connection: str = (
        "mongodb://uasdaq:password@uasdaq-mongodb-0.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-1.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-2.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017/data?replicaSet=uasdaq-mongodb&ssl=false"
    )
    erddap_http_connection: str = (
        "http://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
    )
    erddap_https_connection: str = (
        "https://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
    )
    # erddap_author: str = "fake_author"

    dry_run: bool = False

    class Config:
        env_prefix = "DASHBOARD_"
        case_sensitive = False


# app = Flask(__name__)
# app = Dash(__name__, use_pages=True, url_base_pathname="/uasdaq/dashboard/")
# app = Dash(__name__)#, url_base_pathname="/uasdaq/dashboard/")
# server = app.server
# L.info("dashboard", extra={"app": app, "server": server})
# config = Settings()
# print(config)
# L.info("config settings", extra={"config_settings": config})

# combine secrets to get complete connection string
# if "<username>" in config.mongodb_connection:
#     mongodb_conn = config.mongodb_connection.replace(
#         "<username>", config.mongodb_user_name
#     )
#     config = config.copy(update={"mongodb_connection": mongodb_conn})

# if "<password>" in config.mongodb_connection:
#     mongodb_conn = config.mongodb_connection.replace(
#         "<password>", config.mongodb_user_password
#     )
#     config = config.copy(update={"mongodb_connection": mongodb_conn})


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
#                     self.connection,
#                     # tls=True,
#                     # tlsAllowInvalidCertificates=True
#                 )
#             except pymongo.errors.ConnectionError:
#                 self.client = None
#             L.info("mongo client", extra={"connection": self.connection, "client": self.client})
#         # return self.client

#     def find_one(self, database: str, collection: str, query: dict):
#         self.connect()
#         if self.client:
#             db = self.client[database]
#             db_collection = db[collection]
#             result = db_collection.find_one(query)
#             if result:
#                 update = {"last_update": datetime.now(tz=timezone.utc)}
#                 db_client.update_one(database, collection, result, update)
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


# db_client = DBClient(connection=config.mongodb_connection)

# @app.route("/sensor/data/update", methods=["POST"])
# def sensor_data_update():

#     try:
#         ce = from_http(headers=request.headers, data=request.get_data())
#         # to support local testing...
#         if isinstance(ce.data, str):
#             ce.data = json.loads(ce.data)
#     except InvalidStructuredJSON:
#         L.error("not a valid cloudevent")
#         return "not a valid cloudevent", 400

#     parts = Path(ce["source"]).parts
#     L.info(
#         "db-manager update",
#         extra={"ce-source": ce["source"], "ce-type": ce["type"], "ce-data": ce.data},
#     )

#     try:
#         attributes = ce.data["attributes"]
#         dimensions = ce.data["dimensions"]
#         variables = ce.data["variables"]

#         make = attributes["make"]["data"]
#         model = attributes["model"]["data"]
#         serial_number = attributes["serial_number"]["data"]
#         format_version = attributes["format_version"]["data"]
#         parts = format_version.split(".")
#         erddap_version = f"v{parts[0]}"
#         dataset_id = "::".join([make, model, erddap_version])
#         timestamp = ce.data["timestamp"]

#     except KeyError:
#         L.error("db-manager update error", extra={"sensor": ce.data})
#         return "bad sensor data", 400

#     doc = {
#         # "_id": id,
#         "make": make,
#         "model": model,
#         "serial_number": serial_number,
#         "version": erddap_version,
#         "timestamp": timestamp,
#         "attributes": attributes,
#         "dimensions": dimensions,
#         "variables": variables,
#         # "last_update": datetime.now(tz=timezone.utc),
#     }

#     filter = {
#         "make": make,
#         "model": model,
#         "version": erddap_version,
#         "serial_number": serial_number,
#         "timestamp": timestamp,
#     }

#     update = {"last_update": datetime.now(tz=timezone.utc)}

#     result = db_client.update_one(
#         database="data",
#         collection="sensor",
#         filter=filter,
#         update=update,
#         document=doc,
#         upsert=True,
#     )
#     L.info("db-manager update result", extra={"result": result})
#     # sensor_definition = get_sensor_definition(ce.data)

#     # result = False
#     # if sensor_definition:
#     #     dataset_id, params = get_erddap_insert_sensor_data(
#     #         sensor_definition=sensor_definition, sensor_data=ce.data
#     #     )
#     #     if dataset_id and params:
#     #         result, msg = erddap_client.http_insert(dataset_id, params=params)
#     #     else:
#     #         L.info(
#     #             f"erddap-insert - Didn't send POST to ERRDAP @ {config.erddap_https_connection}"
#     #         )
#     #         # L.info(msg, extra=params)
#     #         return "no params", 400

#     # if result:
#     #     # add to db
#     #     # update_sensor_data_db(ce.data)
#     #     return msg
#     # else:
#     #     id = sensor_definition_id_from_sensor_data(ce.data)
#     #     if not id:
#     #         msg = L.error("can't find sensor_defnition_id")
#     #         return msg

#     #     # sync request message
#     #     msg_type = "sensor.registry.sync"
#     #     msg_source = "uasdaq.erddap-insert"
#     #     sync_request = {"sensor-definition-id-list": [id]}
#     #     attributes = {
#     #         "type": msg_type,
#     #         "source": msg_source,
#     #         "id": str(ULID()),
#     #         "datacontenttype": ce["datacontenttype"],
#     #     }
#     #     ce_sync = CloudEvent(attributes=attributes, data=sync_request)

#     #     # backlog request message
#     #     msg_type = "sensor.data.backlog"
#     #     counter = 1
#     #     # if "backlog-counter" in ce:
#     #     #     counter = ce["backlog-counter"] + 1
#     #     # if counter > config.backlog_max_tries:
#     #     #     # log and return message saying to many tries
#     #     #     msg = L.info(f"erddap-insert - too many attempts")
#     #     #     L.info(msg, extra=params)
#     #     #     return msg

#     #     attributes = {
#     #         "type": msg_type,
#     #         "source": ce["source"],
#     #         "id": ce["id"],
#     #         "datacontenttype": ce["datacontenttype"],
#     #         # "backlog-counter": counter
#     #     }
#     #     backlog_data = {"backlog-counter": counter, "backlog-data": ce.data}
#     #     ce_backlog = CloudEvent(attributes=attributes, data=backlog_data)
#     #     ce_list = [ce_sync, ce_backlog]
#     #     try:
#     #         # send to knative kafkabroker
#     #         with httpx.Client() as client:

#     #             for ce in ce_list:
#     #                 headers, body = to_structured(ce)
#     #                 L.info("headers", extra={"h": headers})
#     #                 r = client.post(
#     #                     config.knative_broker,
#     #                     headers=headers,
#     #                     data=body,
#     #                     # config.knative_broker, headers=headers, data=body.decode()
#     #                 )
#     #                 L.info("erddap_insert", extra={"request": r.request.content})
#     #                 r.raise_for_status()
#     #                 sleep(1)
#     #     except InvalidStructuredJSON:
#     #         L.error(f"INVALID MSG: {ce}")
#     #     except httpx.HTTPError as e:
#     #         L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")

#     #     # sleep(1)
#     #     # # send to erddap-insert-backlog with a counter
#     #     # msg_type = "sensor.data.backlog"
#     #     # # msg_source = ce["source"]
#     #     # counter = 1
#     #     # if "backlog-counter" in ce:
#     #     #     counter = ce["backlog-counter"] + 1
#     #     # if counter > config.backlog_max_tries:
#     #     #     # log and return message saying to many tries
#     #     #     msg = L.info(f"erddap-insert - too many attempts")
#     #     #     L.info(msg, extra=params)
#     #     #     return msg

#     #     # attributes = {
#     #     #     "type": msg_type,
#     #     #     "source": ce["source"],
#     #     #     "id": ce["id"],
#     #     #     "datacontenttype": ce["datacontenttype"],
#     #     #     "backlog-counter": counter
#     #     # }
#     #     # ce = CloudEvent(attributes=attributes, data=ce.data)

#     #     # try:
#     #     #     headers, body = to_structured(ce)
#     #     #     # send to knative kafkabroker
#     #     #     with httpx.Client() as client:
#     #     #         r = client.post(
#     #     #             config.knative_broker,
#     #     #             headers=headers,
#     #     #             data=body,
#     #     #             # config.knative_broker, headers=headers, data=body.decode()
#     #     #         )
#     #     #         L.info(
#     #     #             "erddap_insert backlog", extra={"backlog-request": r.request.content}
#     #     #         )
#     #     #         r.raise_for_status()
#     #     # except InvalidStructuredJSON:
#     #     #     L.error(f"INVALID MSG: {ce}")
#     #     # except httpx.HTTPError as e:
#     #     #     L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")

#     return "ok", 200


# @app.route("/data-db/init", methods=["POST"])
# def data_db_init():
#     L.info("data_db init")
#     L.info("init request", extra={"init-request": request.data})
#     try:
#         ce = from_http(headers=request.headers, data=request.get_data())
#         # to support local testing...
#         if isinstance(ce.data, str):
#             ce.data = json.loads(ce.data)
#     except InvalidStructuredJSON:
#         L.error("not a valid cloudevent")
#         return "not a valid cloudevent", 400

#     parts = Path(ce["source"]).parts
#     L.info(
#         "data-db init",
#         extra={"ce-source": ce["source"], "ce-type": ce["type"], "ce-data": ce.data},
#     )

#     try:
#         data_collections = ce.data["data-collections"]
#     except KeyError:
#         L.error("bad init request")
#         return "find right way to return error"

#     client = pymongo.MongoClient(config.mongodb_connection)
#     L.info("client", extra={"client": client})
#     data = client.data
#     L.info("db", extra={"db": data})

#     try:
#         for dc, cfg in ce.data["data-collections"].items():
#             if cfg["operation"] == "create":
#                 try:
#                     collection = data.create_collection(dc, check_exists=True)
#                     if cfg["ttl"]:
#                         collection.create_index(
#                             [("last_update", 1)], expireAfterSeconds=cfg["ttl"]
#                         )
#                     L.info("data-db-init", extra={"sensor": collection})
#                 except pymongo.errors.CollectionInvalid:
#                     continue
#     except (KeyError, Exception) as e:
#         L.error("db init error", extra={"db_error": e})
#         pass

#     # sensor_type_registry = registry.get_collection("sensor_type")
#     # L.info("collection", extra={"collection": client} )
#     # result = sensor_type_registry.insert_one(ce.data)
#     # L.info("insert", extra={"result": client} )

#     return "ok"


# @app.route("/register/sensor/sync", methods=["POST"])
# def register_sensor_sync():
#     try:
#         ce = from_http(headers=request.headers, data=request.get_data())
#         # to support local testing...
#         if isinstance(ce.data, str):
#             ce.data = json.loads(ce.data)
#     except InvalidStructuredJSON:
#         L.error("not a valid cloudevent")
#         return "not a valid cloudevent", 400

#     parts = Path(ce["source"]).parts
#     L.info(
#         "register sensor",
#         extra={"ce-source": ce["source"], "ce-type": ce["type"], "ce-data": ce.data},
#     )

#     if "sensor-definition-id-list"  in ce.data:
#         for id in ce.data["sensor-definition-id-list"]:
#             update_sensor_definition_db(id)

#     return "ok", 200

# app.layout = html.Div([
#     html.H1('Multi-page app with Dash Pages')
#     # html.Div([
#     #     html.Div(
#     #         dcc.Link(f"{page['name']} - {page['path']}", href=page["relative_path"])
#     #     ) for page in dash.page_registry.values()
#     # ]),
#     # dash.page_container
# ])

# if __name__ == '__main__':
#     app.run(debug=True)

# df = pd.read_csv('https://raw.githubusercontent.com/plotly/datasets/master/gapminder_unfiltered.csv')

# app = Dash(__name__)

# app.layout = html.Div([
#     html.H1(children='Title of Dash App', style={'textAlign':'center'}),
#     dcc.Dropdown(df.country.unique(), 'Canada', id='dropdown-selection'),
#     dcc.Graph(id='graph-content')
# ])

# @callback(
#     Output('graph-content', 'figure'),
#     Input('dropdown-selection', 'value')
# )
# def update_graph(value):
#     dff = df[df.country==value]
#     return px.line(dff, x='year', y='pop')

async def shutdown():
    print("shutting down")
    # for task in task_list:
    #     print(f"cancel: {task}")
    #     task.cancel()

async def main(config):
    config = uvicorn.Config(
        "main:app",
        host=config.host,
        port=config.port,
        # log_level=server_config.log_level,
        root_path="/uasdaq/dashboard",
        # log_config=dict_config,
    )

    server = uvicorn.Server(config)
    # test = logging.getLogger()
    # test.info("test")
    L.info(f"server: {server}")
    await server.serve()

    print("starting shutdown...")
    await shutdown()
    print("done.")


if __name__ == "__main__":
    # app.run(debug=config.debug, host=config.host, port=config.port)
    # app.run()
    config = Settings()
    asyncio.run(main(config))