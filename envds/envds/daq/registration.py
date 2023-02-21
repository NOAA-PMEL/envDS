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


class SensorRegistration(JsonModel):
    make: str = Field(index=True)
    model: str = Field(index=True)
    version: str = Field(index=True)
    checksum: int
    metadata: dict | None = {}


async def init_sensor_registration():
    SensorRegistration.Meta.database = await get_redis_connection(
        url="redis://redis.default"
    )
    await Migrator().run()


async def register_sensor(
    make: str, model: str, version: str = "1.0", metadata: dict = {}
):
    try:
        reg = SensorRegistration(
            make=make,
            model=model,
            version=version,
            checksum=get_checksum(metadata),
            metadata=metadata,
        )
        await reg.save()
    except ValidationError as e:
        print(f"Could not register sensor: \n{e}")


async def get_sensor_registration(
    make: str, model: str, version: str = "1.0"
) -> SensorRegistration:
    reg = await SensorRegistration.find(
        SensorRegistration.make == make
        and SensorRegistration.model == model
        and SensorRegistration.version == version
    ).first()
    return reg


async def get_sensor_metadata(make: str, model: str, version: str = "1.0") -> dict:
    reg = await get_sensor_registration(make=make, model=model, version=version)
    if reg:
        return reg.metadata
    return {}
