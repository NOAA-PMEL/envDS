import asyncio
from aredis_om import (
    EmbeddedJsonModel,
    JsonModel,
    Field,
    Migrator,
    get_redis_connection,
)
from pydantic import ValidationError
from envds.util.util import get_checksum

from datetime import datetime
import os

async def init_model_type(model_type):
    # print("init_model_type")
    # model_type.Meta.database = await get_redis_connection(
    #     url="redis://redis.default"
    # )
    # print(f"init_model_type: {model_type.Meta.database}")
    await Migrator().run()
    print("init_model_type: done")

async def get_model_by_pk(model_type, pk):
    return await model_type.get(pk)

async def save_model(model):
    await model.save()

async def delete_model(model):
    await model.delete()

async def expire_model(model, expire: int = 300):
    model.expire(expire)