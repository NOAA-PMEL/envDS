from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
# from cloudevents.http import from_http
from cloudevents.conversion import from_http
from cloudevents.pydantic import CloudEvent

# from typing import Union
from pydantic import BaseModel

from apis.router import api_router

app = FastAPI()

origins = ["*"]     # dev
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

app.include_router(api_router)#, prefix="/envds/home")
# app.include_router(router)

# @app.on_event("startup")
# async def start_system():
#     print("starting system")

# @app.on_event("shutdown")
# async def start_system():
#     print("stopping system")

@app.get("/")
async def root():
    return {"message": "Hello World from DAQ"}

# @app.post("/ce")
# async def handle_ce(ce: CloudEvent):
#     # print(ce.data)
#     # print(from_http(ce))
#     # header, data = from_http(ce)
#     print(f"type: {ce['type']}, source: {ce['source']}, data: {ce.data}, id: {ce['id']}")
#     print(f"attributes: {ce}")
#     # event = from_http(ce.headers, ce.get_data)
#     # print(event)