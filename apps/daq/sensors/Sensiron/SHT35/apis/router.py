from fastapi import APIRouter

from apis.v1 import route_cloudevents

api_router = APIRouter()
api_router.include_router(route_cloudevents.router, prefix="/api/v1/ce", tags=["cloudevents"])