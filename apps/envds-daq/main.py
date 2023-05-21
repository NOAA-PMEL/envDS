from fastapi import (
    FastAPI,
    APIRouter,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

# from cloudevents.http import from_http
from cloudevents.conversion import from_http
from cloudevents.pydantic import CloudEvent

# from typing import Union
from pydantic import BaseModel
import json
from apis.router import api_router
import socket

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
    get_sensor_type_metadata,
)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

origins = ["*"]  # dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
# home_router = APIRouter()

# @home_router.get("/")
# async def home():
#     return {"message": "Hello World"}

# home_router.include_router(api_router)
# router.include_router(home_router)#, prefix="/envds/home")

app.include_router(api_router)  # , prefix="/envds/home")
# app.include_router(router)

# @app.on_event("startup")
# async def start_system():
#     print("starting system")

# @app.on_event("shutdown")
# async def start_system():
#     print("stopping system")
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # print(f"active connections: {self.active_connections}")
        # await websocket.broadcast("test message")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    async def broadcast_exclude_self(self, message: str, websocket: WebSocket):
        for connection in self.active_connections:
            if connection != websocket:
                await connection.send_text(message)


manager = ConnectionManager()
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
print(f"name: {host_name}, ip: {host_ip}")


@app.get("/")
async def root():
    return {"message": "Hello World from DAQ"}


@app.get("/sensor/{make}/{model}/{serial_number}", response_class=HTMLResponse)
async def sensor(request: Request, make: str, model: str, serial_number: str):
    # get sensor definition
    # send context info to template
    meta = await get_sensor_type_metadata(make, model)
    reg = await get_sensor_registration(make, model, serial_number)
    host_name = socket.gethostname()
    host_ip = socket.gethostbyname(host_name)
    if not meta or not reg:
        raise HTTPException(status_code=404, detail="Sensor definition not found")
    print(f"reg: {reg}")
    # print(f"meta: {meta}")
    title = f"sensor::{make}::{model}"

    return templates.TemplateResponse(
        "sensor.html",
        {
            "request": request,
            "title": title,
            "ws_host": host_name,
            "ws_ip": host_ip,
            "sensor_meta": meta,
            "sensor_reg": reg.dict(),
        },
    )


@app.websocket("/ws/sensor/{make}/{model}/{serial_number}")
# @app.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket, make: str, model: str, serial_number: str
):
# async def websocket_endpoint(
#     websocket: WebSocket,
#     client_id: int
# ):
    # try:
    #     print(f"websocket: {websocket}")
    await manager.connect(websocket)
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
            await manager.broadcast_exclude_self(data, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # await manager.broadcast(f"Client left the chat")

    # await websocket.send_text(
    #     f"Session cookie or query token value is: {cookie_or_token}"
    # )
    # if q is not None:
    #     await websocket.send_text(f"Query parameter q is: {q}")
    # await websocket.send_text(f"Message text was: {data}, for item ID: {item_id}")


# return {"make": make, "model": model, "serial_number": serial_number}


# @app.post("/ce")
# async def handle_ce(ce: CloudEvent):
#     # print(ce.data)
#     # print(from_http(ce))
#     # header, data = from_http(ce)
#     print(f"type: {ce['type']}, source: {ce['source']}, data: {ce.data}, id: {ce['id']}")
#     print(f"attributes: {ce}")
#     # event = from_http(ce.headers, ce.get_data)
#     # print(event)
