from fastapi import APIRouter
# from cloudevents.http import from_http
from cloudevents.conversion import from_http
from cloudevents.pydantic import CloudEvent

router = APIRouter()

@router.post("/apply")
def handle_cloudevents(event: CloudEvent):
    pass
