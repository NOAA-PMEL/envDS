import os
import asyncio
from redis_om import get_redis_connection
from aredis_om import (
    EmbeddedJsonModel,
    JsonModel,
    Field,
    Migrator,
    # get_redis_connection,
    NotFoundError,
)
from pydantic import ValidationError
from envds.util.util import get_checksum

from envds.util.util import get_datetime_string

# from envds.daq.sensor import Sensor

from envds.db.db_redis import init_model_type, save_model, delete_model, expire_model
from datetime import datetime

# TODO: how to abstract to allow redis, mongo, etc as db?

# def get_connection():
#     return get_redis_connection(url="redis://redis.default")


class SensorTypeRegistration(JsonModel):
    make: str = Field(index=True)
    model: str = Field(index=True)
    version: str = Field(index=True)
    checksum: str
    creation_date = str
    metadata: dict = {}

    # class Meta:
    #     database = get_connection()


class SensorRegistration(JsonModel):
    make: str = Field(index=True)
    model: str = Field(index=True)
    serial_number: str = Field(index=True)
    source_id: str
    creation_date = datetime

class SensorDataRecord(JsonModel):
    make: str = Field(index=True)
    model: str = Field(index=True)
    serial_number: str = Field(index=True)
    timestamp: datetime = Field(index=True)
    source_id: str = Field(index=True)
    data: dict

    # class Meta:
    #     database = get_connection()


async def init_db_models():
    # print(f"init_sensor_type_registration: {SensorTypeRegistration.Meta.database}")
    # await init_model_type(SensorTypeRegistration)
    # print("init_sensor_type_registration: done")
    # SensorTypeRegistration.Meta.database = await get_redis_connection(
    #     url="redis://redis.default"
    # )
    await Migrator().run()


async def init_sensor_registration():
    await init_model_type(SensorRegistration)


# async def register_sensor_type_as_sensor(sensor: Sensor, version: str = "1.0.0"):
#     await register_sensor_type(
#         make=sensor.get_make(),
#         model=sensor.get_model(),
#         version=version,
#         metadata=sensor.get_sensor_type_metadata()
#     )


async def register_sensor_type(
    make: str, model: str, version: str = "1.0.0", creation_date: str = None, metadata: dict = {}
):
    print(f'redis url: {os.getenv("REDIS_OM_URL")}')
    try:
        print("here:1")
        if creation_date is None:
            # creation_date = datetime.utcnow()
            creation_date = get_datetime_string()
        reg = SensorTypeRegistration(
            make=make,
            model=model,
            version=version,
            checksum=get_checksum(metadata),
            creation_date=creation_date,
            metadata=metadata,
        )
        print("here:2")
        current = await get_sensor_type_registration(
            make=make, model=model, version=version
        )
        print(f"make: {make}, model: {model}, version: {version}")
        print("here:3")
        # current = await SensorTypeRegistration.find(
        #     SensorTypeRegistration.make == make
        #     and SensorTypeRegistration.model == model
        #     and SensorTypeRegistration.version == version
        # ).first()
        print(f"current: {current}")
        if current:
            if current.checksum == reg.checksum:
                print(f"current exists: {current}, {current.creation_date}, {reg.creation_date}")
                print(f"compare: {current.creation_date > reg.creation_date}")
                return
            else:
                try:
                    if current.creation_date > reg.creation_date:
                        print("current registration is newer")
                        return
                except TypeError as e:
                    print(f"registration typeerror: {e}")
                    pass
                await SensorTypeRegistration.delete(current.pk)

        print(f"reg({reg.pk}): {reg}")
        await reg.save()
        # await save_model(reg)
    except (ValidationError, Exception) as e:
        print(f"Could not register sensor: \n{e}")


# TODO: abstract the find method?
async def get_sensor_type_registration(
    make: str, model: str, version: str = "1.0.0"
) -> SensorTypeRegistration:
    try:
        reg = await SensorTypeRegistration.find(
            SensorTypeRegistration.make == make,
            SensorTypeRegistration.model == model,
            SensorTypeRegistration.version == version
        ).first()
        print(f"{make}-{model}-{version}: {reg}")
        return reg
    except NotFoundError as e:
        print(f"get_sensor_type error: {e}")
        return None


async def get_sensor_type_metadata(make: str, model: str, version: str = "1.0.0") -> dict:
    reg = await get_sensor_type_registration(make=make, model=model, version=version)
    if reg:
        return reg.metadata
    return {}


async def register_sensor(
    make: str, model: str, serial_number: str, source_id: str, expire: int = 300
):
    try:

        reg = SensorRegistration(
            make=make,
            model=model,
            serial_number=serial_number,
            creation_date=datetime.utcnow(),
            source_id=source_id,
        )

        current = await get_sensor_registration(
            make=make,
            model=model,
            serial_number=serial_number,
        )
        # current = await SensorRegistration.find(
        #     SensorRegistration.make == make
        #     and SensorRegistration.model == model
        #     and SensorRegistration.serial_number == serial_number
        # ).first()
        print(f"current: {current}")
        if current:
            await current.expire(expire)
            return

        print(f"reg({reg.pk}): {reg}")
        await reg.save()
        # await save_model(reg)
        await reg.expire(expire)
        # await expire_model(reg, expire=expire)
    except (ValidationError, Exception) as e:
        print(f"Could not register sensor: \n{e}")


async def get_sensor_registration(
    make: str, model: str, serial_number: str
) -> SensorRegistration:
    try:
        reg = await SensorRegistration.find(
            SensorRegistration.make == make,
            SensorRegistration.model == model,
            SensorRegistration.serial_number == serial_number
        ).first()
        return reg

    except NotFoundError as e:
        print(f"get_sensor error: {e}")
        return None

async def get_sensor_type_registration_by_pk(pk) -> SensorTypeRegistration:
    try:
        reg = SensorTypeRegistration.get(pk)
        return reg
    except NotFoundError:
        return None

async def get_sensor_registration_by_pk(pk) -> SensorRegistration:
    try:
        reg = await SensorRegistration.get(pk)
        return reg
    except NotFoundError:
        return None

async def get_all_sensor_registration() -> list[SensorRegistration]:
    try:
        regs = await SensorRegistration.find().all()
        return regs

    except NotFoundError as e:
        print(f"get_sensor error: {e}")
        return None

async def get_all_sensor_type_registration() -> list[SensorTypeRegistration]:
    try:
        regs = await SensorTypeRegistration.find().all()
        return regs

    except NotFoundError as e:
        print(f"get_sensor_type error: {e}")
        return None
