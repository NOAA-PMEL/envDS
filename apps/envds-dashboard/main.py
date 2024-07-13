import asyncio
from datetime import datetime, timezone
import json
import logging
import socket
from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware

from cloudevents.http import CloudEvent, from_http
from cloudevents.conversion import to_structured  # , from_http
from cloudevents.exceptions import InvalidStructuredJSON

# from typing import Union
import httpx
from logfmter import Logfmter
from pydantic import BaseModel, BaseSettings
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from ulid import ULID

from dashapp import app as dash_app

# from apis.router import api_router
handler = logging.StreamHandler()
handler.setFormatter(Logfmter())
logging.basicConfig(handlers=[handler])
L = logging.getLogger(__name__)
L.setLevel(logging.INFO)

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8787
    debug: bool = False
    knative_broker: str = (
        "http://kafka-broker-ingress.knative-eventing.svc.cluster.local/default/default"
    )
    mongodb_data_user_name: str = ""
    mongodb_data_user_password: str = ""
    mongodb_registry_user_name: str = ""
    mongodb_registry_user_password: str = ""
    mongodb_data_connection: str = (
        "mongodb://uasdaq:password@uasdaq-mongodb-0.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-1.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-2.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017/data?replicaSet=uasdaq-mongodb&ssl=false"
    )
    mongodb_registry_connection: str = (
        "mongodb://uasdaq:password@uasdaq-mongodb-0.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-1.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017,uasdaq-mongodb-2.uasdaq-mongodb-svc.mongodb.svc.cluster.local:27017/registry?replicaSet=uasdaq-mongodb&ssl=false"
    )
    # erddap_http_connection: str = (
    #     "http://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
    # )
    # erddap_https_connection: str = (
    #     "https://uasdaq.pmel.noaa.gov/uasdaq/dataserver/erddap"
    # )
    # erddap_author: str = "fake_author"

    dry_run: bool = False

    class Config:
        env_prefix = "DASHBOARD_"
        case_sensitive = False

config = Settings()
# L.info("config settings", extra={"config_settings": config})

# TODO: add readOnly user for this connection

# combine secrets to get complete connection string
if "<username>" in config.mongodb_data_connection:
    mongodb_data_conn = config.mongodb_data_connection.replace(
        "<username>", config.mongodb_data_user_name
    )
    config = config.copy(update={"mongodb_data_connection": mongodb_data_conn})

if "<password>" in config.mongodb_data_connection:
    mongodb_data_conn = config.mongodb_data_connection.replace(
        "<password>", config.mongodb_data_user_password
    )
    config = config.copy(update={"mongodb_data_connection": mongodb_data_conn})

if "<username>" in config.mongodb_registry_connection:
    mongodb_registry_conn = config.mongodb_registry_connection.replace(
        "<username>", config.mongodb_registry_user_name
    )
    config = config.copy(update={"mongodb_registry_connection": mongodb_registry_conn})

if "<password>" in config.mongodb_registry_connection:
    mongodb_registry_conn = config.mongodb_registry_connection.replace(
        "<password>", config.mongodb_registry_user_password
    )
    config = config.copy(update={"mongodb_registry_connection": mongodb_registry_conn})
print(mongodb_registry_conn)

class DBClient:
    def __init__(self, connection: str, db_type: str = "mongodb") -> None:
        self.db_type = db_type
        self.client = None
        self.connection = connection

    def connect(self):
        if self.db_type == "mongodb":
            self.connect_mongo()
        # return self.client

    def connect_mongo(self):
        if not self.client:
            try:
                # self.client = pymongo.MongoClient(
                self.client = AsyncIOMotorClient(
                    self.connection,
                    connect=True,
                    # tls=True,
                    # tlsAllowInvalidCertificates=True
                )
            except pymongo.errors.ConnectionError:
                self.client = None
            L.info("mongo client", extra={"connection": self.connection, "client": self.client})
            # L.info(await self.client.server_info())
        # return self.client

    def get_db(self, database: str):
        self.connect()
        if self.client:
            return self.client[database]
        return None
    
    def get_collection(self, database: str, collection: str):
        L.info("get_collection")
        db = self.get_db(database)
        L.info(f"get_collection:db = {db}")
        if db is not None:
            try:
                db_coll = db[collection]
                L.info(f"get_collection:db:collection = {db_coll}")
                return db_coll
            except Exception as e:
                L.error(f"get_collection error: {e}")
        return None
 
    async def find_one(self, database: str, collection: str, query: dict):
        self.connect()
        if self.client:
            db = self.client[database]
            db_collection = db[collection]
            result = await db_collection.find_one(query)
            if result:
                update = {"last_update": datetime.now(tz=timezone.utc)}
                await db_data_client.update_one(database, collection, result, update)
            return result
        return None

    async def insert_one(self, database: str, collection: str, document: dict):
        self.connect()
        if self.client:
            db = self.client[database]
            sensor_defs = db[collection]
            result = await sensor_defs.insert_one(document)
            return result
        return None

    async def update_one(
        self,
        database: str,
        collection: str,
        document: dict,
        update: dict,
        filter: dict = None,
        upsert=False,
    ):
        self.connect()
        if self.client:
            db = self.client[database]
            sensor = db[collection]
            if filter is None:
                filter = document
            set_update = {"$set": update}
            if upsert:
                set_update["$setOnInsert"] = document
            result = await sensor.update_one(filter=filter, update=set_update, upsert=upsert)
            return result
        return None


db_data_client = DBClient(connection=config.mongodb_data_connection)
db_registry_client = DBClient(connection=config.mongodb_registry_connection)

app = FastAPI()

origins = ["*"]  # dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()

app.mount("/dash", WSGIMiddleware(dash_app.server))

task_map = {}

                        
class ConnectionManager:
    def __init__(self):
        # self.active_connections: list[WebSocket] = []
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, client_type: str, client_id: str):
        print(f"{client_type}: {client_id}")
        await websocket.accept()
        if client_type not in self.active_connections:
            self.active_connections[client_type] = dict()
        if client_id not in self.active_connections[client_type]:
            # self.active_connections[source_type][source_id] = list[WebSocket]
            self.active_connections[client_type][client_id] = []
        print(f"active_connections: {self.active_connections}")
        self.active_connections[client_type][client_id].append(websocket)
        print(f"active_connections: {self.active_connections}")
        # self.active_connections.append(websocket)
        # print(f"active connections: {self.active_connections}")
        # await websocket.broadcast("test message")

    async def disconnect(self, websocket: WebSocket):
        for client_type, types in self.active_connections.items():
            for client_id, ws_list in types.items():
                if websocket in ws_list:
                    ws_list.remove(websocket)
                    if websocket:
                        await websocket.close()
                    return
        # self.active_connections.remove(websocket)

    async def send_personal_message(
        self, message: str, websocket: WebSocket, client_type: str, client_id: str
    ):
        await websocket.send_text(message)

    async def broadcast(self, message: str, client_type: str, client_id: str):
        try:
            # L.info(f"{client_type}/{client_id}")#: {message}")
            # L.info(f"{self.active_connections}")
            # L.info("check dictionary", extra={"type_in_ac": f"{client_type in self.active_connections}"})
            for connection in self.active_connections[client_type][client_id]:
                # L.info(f"broadcast: {connection}, {message}")
                await connection.send_text(message)
                # await asyncio.sleep(.1)
        except (KeyError, Exception) as e:
            # L.info(f"broadcast error: {e}")
            pass

    async def broadcast_exclude_self(
        self, message: str, websocket: WebSocket, client_type: str, client_id: str
    ):
        # for connection in self.active_connections:
        #     if connection != websocket:
        #         await connection.send_text(message)
        try:
            for connection in self.active_connections[client_type][client_id]:
                print(f"connection: {connection}\nws: {websocket}")
                if connection != websocket:
                    await connection.send_text(message)
        except KeyError:
            pass

manager = ConnectionManager()
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
print(f"name: {host_name}, ip: {host_ip}")


async def watch_registry_collection(db_client, collection, ws_manager, ws_client_type, ws_client_id, op_types=["insert", "update", "replace", "delete"]):
    # db = db_client.get_db(database)
    database = "registry"
    db_collection = db_client.get_collection(database, collection)
    # L.info(f"db_collection: {db_collection}")
    if db_collection is None:
        L.error("watch_db: can't get collection", extra={"db": database, "collection": collection})
        return

    # get current data
    try:
        async for document in db_collection.find():
            # L.info("+++watch_registry_collection:document", extra={"doc": document})
            if not isinstance(document["_id"], str):
                document["_id"] = str(document["_id"])
            result = {
                "database": database,
                "collection": collection,
                "operation-type": "insert",
                "data": document
                # "data": "test"
            }
            # L.info(f"data:keys: {result["data"].keys()}")
            # if result:
            if result["data"] and "last_update" in result["data"]:
                result["data"].pop("last_update")
            
            # L.info(f"result: {json.dumps(result)}")
            # L.info(f"{manager}, {ws_client_type}, {ws_client_id}")
            await ws_manager.broadcast(json.dumps(result),client_type=ws_client_type, client_id=ws_client_id)
            await asyncio.sleep(.1)
    except Exception as e:
        L.error("watch_registry_collection error", extra={"error": e})

    pipeline = []
    for op_type in op_types:
        pipeline.append({'$match': {'operationType': op_type}})
        # break
    
    L.info(f"pipeline: {pipeline}")
    resume_token = None
    message = {"test": 0}
    while True:
        # try:
        #     L.info(f"message: {message}")
        #     await ws_manager.broadcast(json.dumps(message),client_type=ws_client_type, client_id=ws_client_id)
        #     message["test"] += 1
        # except Exception as e:
        #     L.error(f"error: {e}")
        # # ctr +=1
        # await asyncio.sleep(1)
        try:
            # pipeline = [{'$match': {'operationType': 'insert'}}]
            L.info(f"collection: {db_collection}")
            # async with db_collection.watch(resume_after=resume_token, full_document="updateLookup") as stream:
            async with db_collection.watch(full_document="updateLookup", full_document_before_change='whenAvailable') as stream:
                    # pipeline, resume_after=resume_token, full_document="updateLookup") as stream:
                L.info(f"stream: {stream}")
                async for change in stream:
                    # L.info(f"change: {change}")
                    try:
                        if change["operationType"] == "delete":
                            document = change.get("fullDocumentBeforeChange", None)
                        else:
                            document = change.get("fullDocument", None)

                        if not isinstance(document["_id"], str):
                            document["_id"] = str(document["_id"])

                        result = {
                            "database": database,
                            "collection": collection,
                            "operation-type": change["operationType"],
                            # "data": change.get("fullDocument", None)
                            "data": document
                            # "data": "test"
                        }
                        # L.info(f"data:keys: {result["data"].keys()}")
                        # if result:
                        if result["data"] and "last_update" in result["data"]:
                            result["data"].pop("last_update")
                        # L.info(f"result: {json.dumps(result)}")
                        # L.info(f"{manager}, {ws_client_type}, {ws_client_id}")
                        await ws_manager.broadcast(json.dumps(result),client_type=ws_client_type, client_id=ws_client_id)
                        await asyncio.sleep(.1)
                    except Exception as e:
                        L.error(f"broacast error: {e}")
                L.info("out of for loop")
            L.info("out of with loop")
        except (pymongo.errors.PyMongoError, Exception):
            # The ChangeStream encountered an unrecoverable error or the
            # resume attempt failed to recreate the cursor.
            if resume_token is None:
                # There is no usable resume token because there was a
                # failure during ChangeStream initialization.
                L.error('Failure watching collection', extra={"db": database, "collection": collection})
                return
            # else:
            #     # Use the interrupted ChangeStream's resume token to create
            #     # a new ChangeStream. The new stream will continue from the
            #     # last seen insert change without missing any events.
            #     with db.collection.watch(
            #             pipeline, resume_after=resume_token) as stream:
            #         for insert_change in stream:
            #             print(insert_change)
            #             manager
        L.info("out of try/except")

async def test_task():
    cnt = 0
    while True:
        L.info(f"test_task:{cnt}")
        cnt+=1
        await asyncio.sleep(1)

@app.get("/")
async def root():
    return {"message": "Hello World from UAS-DAQ Dashboard"}

@app.websocket("/ws/sensor/{client_id}")
# @app.websocket("/ws/{client_id}")
async def sensor_ws_endpoint(
    websocket: WebSocket,
    client_id: str
):
    await manager.connect(websocket, client_type="sensor", client_id=client_id)
    print(f"websocket_endpoint: {websocket}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"sensor data: {data}")
            message = json.loads(data)
            if "client-request" in message:
                # await manager.broadcast(json.dumps(message), "sensor", client_id)
                if message['client-request'] == "start-updates":

                    # start task to watch registry.sensor_definition collection for changes
                    # L.info(f"task_map: {task_map}")
                    # if "sensor-definition" in task_map:
                    #     if task_map["sensor-definition"].done():
                    #         task_map.pop("sensor-definition")
                    # if "sensor-definition" not in task_map:
                    #     # task_map["sensor-definition"].cancel()
                    #     L.info("sensor_definition create_task")
                    #     # task_map["sensor-definition"] = asyncio.create_task(test_task())
                    #     task_map["sensor-definition"] = asyncio.create_task(
                    #         watch_registry_collection(
                    #             db_client=db_registry_client,
                    #             # database="registry",
                    #             collection="sensor_definition",
                    #             ws_manager=manager,
                    #             ws_client_type="sensor-registry",
                    #             ws_client_id=client_id
                    #         )
                    #     )

                    # start task to watch registry.sensor collection for changes
                    # L.info(f"task_map: {task_map}")
                    # if "active-sensor" in task_map:
                    #     if task_map["active-sensor"].done():
                    #         task_map.pop("active-sensor")
                    # if "active-sensor" not in task_map:
                    #     # task_map["sensor-definition"].cancel()
                    #     L.info("active-sensor create_task")
                    #     # task_map["sensor-definition"] = asyncio.create_task(test_task())
                    #     task_map["active-sensor"] = asyncio.create_task(
                    #         watch_registry_collection(
                    #             db_client=db_registry_client,
                    #             # database="registry",
                    #             collection="sensor",
                    #             ws_manager=manager,
                    #             ws_client_type="sensor-registry",
                    #             ws_client_id=client_id
                    #         )
                    #     )
                    # L.info(f"task_map: {task_map}")


                    # send request to update sensor-definitions in the db
                    # L.info("register_request", extra={"arg_type": type(reg_request)})
                    msg_type = "sensor.registry.request"

                    attributes = {
                            "type": msg_type,
                            "source": "uasdaq.dashboard",
                            "id": str(ULID()),
                            "datacontenttype": "application/json; charset=utf-8",
                        }
                    reg_request = {"register-sensor-request": "update-sensor-definition-all"}
                    ce = CloudEvent(attributes=attributes, data=reg_request)

                    try:
                        headers, body = to_structured(ce)
                        # send to knative kafkabroker
                        with httpx.Client() as client:
                            r = client.post(
                                config.knative_broker, headers=headers, data=body
                                # config.knative_broker, headers=headers, data=body.decode()
                            )
                            L.info("register-request send", extra={"register-request": r.request.content})
                            # r.raise_for_status()
                    except InvalidStructuredJSON:
                        L.error(f"INVALID MSG: {ce}")
                    except httpx.HTTPError as e:
                        L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")
    except WebSocketDisconnect:
        L.info(f"websocket disconnect: {websocket}")
        await manager.disconnect(websocket)
        await asyncio.sleep(.1)
        # await manager.broadcast(f"Client left the chat")

@app.websocket("/ws/sensor-registry/{client_id}")
# @app.websocket("/ws/{client_id}")
async def sensor_registry_ws_endpoint(
    websocket: WebSocket,
    client_id: str
):
    await manager.connect(websocket, client_type="sensor-registry", client_id=client_id)
    print(f"websocket_endpoint: {websocket}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"main data: {data}")
            message = json.loads(data)
            if "client-request" in message:
                # await manager.broadcast(json.dumps(message), "sensor", client_id)
                if message['client-request'] == "start-updates":

                    # start task to watch registry.sensor_definition collection for changes
                    # L.info(f"task_map: {task_map}")
                    # if "sensor-definition" in task_map:
                    #     if task_map["sensor-definition"].done():
                    #         task_map.pop("sensor-definition")
                    # if "sensor-definition" not in task_map:
                    #     # task_map["sensor-definition"].cancel()
                    #     L.info("sensor_definition create_task")
                    #     # task_map["sensor-definition"] = asyncio.create_task(test_task())
                    #     task_map["sensor-definition"] = asyncio.create_task(
                    #         watch_registry_collection(
                    #             db_client=db_registry_client,
                    #             # database="registry",
                    #             collection="sensor_definition",
                    #             ws_manager=manager,
                    #             ws_client_type="sensor-registry",
                    #             ws_client_id=client_id
                    #         )
                    #     )

                    # start task to watch registry.sensor collection for changes
                    # L.info(f"task_map: {task_map}")
                    # if "active-sensor" in task_map:
                    #     if task_map["active-sensor"].done():
                    #         task_map.pop("active-sensor")
                    # if "active-sensor" not in task_map:
                    #     # task_map["sensor-definition"].cancel()
                    #     L.info("active-sensor create_task")
                    #     # task_map["sensor-definition"] = asyncio.create_task(test_task())
                    #     task_map["active-sensor"] = asyncio.create_task(
                    #         watch_registry_collection(
                    #             db_client=db_registry_client,
                    #             # database="registry",
                    #             collection="sensor",
                    #             ws_manager=manager,
                    #             ws_client_type="sensor-registry",
                    #             ws_client_id=client_id
                    #         )
                    #     )
                    # L.info(f"task_map: {task_map}")


                    # send request to update sensor-definitions in the db
                    # L.info("register_request", extra={"arg_type": type(reg_request)})
                    msg_type = "sensor.registry.request"

                    attributes = {
                            "type": msg_type,
                            "source": "uasdaq.dashboard",
                            "id": str(ULID()),
                            "datacontenttype": "application/json; charset=utf-8",
                        }
                    reg_request = {"register-sensor-request": "update-sensor-definition-all"}
                    ce = CloudEvent(attributes=attributes, data=reg_request)

                    try:
                        headers, body = to_structured(ce)
                        # send to knative kafkabroker
                        with httpx.Client() as client:
                            r = client.post(
                                config.knative_broker, headers=headers, data=body
                                # config.knative_broker, headers=headers, data=body.decode()
                            )
                            L.info("register-request send", extra={"register-request": r.request.content})
                            # r.raise_for_status()
                    except InvalidStructuredJSON:
                        L.error(f"INVALID MSG: {ce}")
                    except httpx.HTTPError as e:
                        L.error(f"HTTP Error when posting to {e.request.url!r}: {e}")
    except WebSocketDisconnect:
        L.info(f"websocket disconnect: {websocket}")
        await manager.disconnect(websocket)
        await asyncio.sleep(.1)
        # await manager.broadcast(f"Client left the chat")

@app.websocket("/ws/chat/{client_id}")
# @app.websocket("/ws/{client_id}")
async def chat_ws_endpoint(
    websocket: WebSocket,
    client_id: str
):
    await manager.connect(websocket, client_type="chat", client_id=client_id)
    print(f"websocket_endpoint: {websocket}")
    #     await websocket.accept()
    #     while True:
    #         data = await websocket.receive_text()
    #         print(data)
    # except Exception as e:
    #     print(f"error: {e}")
    try:
        while True:
            data = await websocket.receive_text()
            print(f"data: {data}")
            # await manager.send_personal_message(f"You wrote: {data}", websocket)
            await manager.broadcast_exclude_self(data, websocket, client_type="chat", client_id=client_id)
            # await manager.broadcast(data, client_type="chat", client_id=client_id)
    except WebSocketDisconnect:
        L.info(f"websocket disconnect: {websocket}")
        await manager.disconnect(websocket)
        # await manager.broadcast(f"Client left the chat")

    # await websocket.send_text(
    #     f"Session cookie or query token value is: {cookie_or_token}"
    # )
    # if q is not None:
    #     await websocket.send_text(f"Query parameter q is: {q}")
    # await websocket.send_text(f"Message text was: {data}, for item ID: {item_id}")


# @app.websocket("/ws/sensor/{make}/{model}/{serial_number}")
# # @app.websocket("/ws/{client_id}")
# async def websocket_endpoint(
#     websocket: WebSocket, make: str, model: str, serial_number: str
# ):
# # async def websocket_endpoint(
# #     websocket: WebSocket,
# #     client_id: int
# # ):
#     # try:
#     #     print(f"websocket: {websocket}")
#     source_id = get_id(make=make, model=model, serial_number=serial_number)
#     await manager.connect(websocket, client_type="sensor", client_id=source_id)
#     print(f"websocket_endpoint: {websocket}")
#     #     await websocket.accept()
#     #     while True:
#     #         data = await websocket.receive_text()
#     #         print(data)
#     # except Exception as e:
#     #     print(f"error: {e}")
#     try:
#         while True:
#             data = await websocket.receive_text()
#             print(f"data: {data}")
#             # await manager.send_personal_message(f"You wrote: {data}", websocket)
#             await manager.broadcast_exclude_self(data, websocket, client_type="sensor", client_id=source_id)
#     except WebSocketDisconnect:
#         manager.disconnect(websocket)
#         # await manager.broadcast(f"Client left the chat")

#     # await websocket.send_text(
#     #     f"Session cookie or query token value is: {cookie_or_token}"
#     # )
#     # if q is not None:
#     #     await websocket.send_text(f"Query parameter q is: {q}")
#     # await websocket.send_text(f"Message text was: {data}, for item ID: {item_id}")

# @app.post("/ce")
# async def handle_ce(ce: CloudEvent):
#     # print(ce.data)
#     # print(from_http(ce))
#     # header, data = from_http(ce)
#     print(f"type: {ce['type']}, source: {ce['source']}, data: {ce.data}, id: {ce['id']}")
#     print(f"attributes: {ce}")
#     # event = from_http(ce.headers, ce.get_data)
#     # print(event)

@app.post("/sensor/data/update")
async def sensor_data_update(request: Request):

    data = await request.body()
    headers = dict(request.headers)

    try:
        ce = from_http(headers=headers, data=data)
        # to support local testing...
        if isinstance(ce.data, str):
            ce.data = json.loads(ce.data)
    except InvalidStructuredJSON:
        L.error("not a valid cloudevent")
        return "not a valid cloudevent", 400

    # parts = Path(ce["source"]).parts
    # L.info(
    #     "db-manager update",
    #     extra={"ce-source": ce["source"], "ce-type": ce["type"], "ce-data": ce.data},
    # )

    try:
        attributes = ce.data["attributes"]
        # dimensions = ce.data["dimensions"]
        # variables = ce.data["variables"]

        make = attributes["make"]["data"]
        model = attributes["model"]["data"]
        serial_number = attributes["serial_number"]["data"]
        # format_version = attributes["format_version"]["data"]
        # parts = format_version.split(".")
        # erddap_version = f"v{parts[0]}"
        sensor_id = "::".join([make, model, serial_number])
        # timestamp = ce.data["timestamp"]

    except KeyError:
        L.error("dashboard sensor update error", extra={"sensor": ce.data})
        return "bad sensor data", 400

    await manager.broadcast(json.dumps(ce.data), "sensor", sensor_id)

    # # update data
    # doc = {
    #     # "_id": id,
    #     "make": make,
    #     "model": model,
    #     "serial_number": serial_number,
    #     "version": erddap_version,
    #     "timestamp": timestamp,
    #     "attributes": attributes,
    #     "dimensions": dimensions,
    #     "variables": variables,
    #     # "last_update": datetime.now(tz=timezone.utc),
    # }

    # filter = {
    #     "make": make,
    #     "model": model,
    #     "version": erddap_version,
    #     "serial_number": serial_number,
    #     "timestamp": timestamp,
    # }

    # update = {"last_update": datetime.now(tz=timezone.utc)}

    # result = db_data_client.update_one(
    #     database="data",
    #     collection="sensor",
    #     filter=filter,
    #     update=update,
    #     document=doc,
    #     upsert=True,
    # )
    # L.info("db-manager data update result", extra={"result": result})

    # # update active sensors
    # # TODO: how to get sampling system?
    # sampling_system = ""
    # doc = {
    #     "_id": sensor_id,
    #     "make": make,
    #     "model": model,
    #     "serial_number": serial_number,
    #     "version": erddap_version,
    #     "sampling_system": sampling_system
    # }

    # filter = {
    #     "_id": sensor_id,
    # }

    # update = {"last_update": datetime.now(tz=timezone.utc)}

    # result = db_registry_client.update_one(
    #     database="registry",
    #     collection="sensor",
    #     filter=filter,
    #     update=update,
    #     document=doc,
    #     upsert=True,
    # )
    # L.info("db-manager registry update result", extra={"result": result})

    return "ok", 200
