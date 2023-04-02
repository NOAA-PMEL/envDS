from pydantic import BaseModel, ValidationError, validator
from typing import Any
import json

metadata = {
    "attributes": {
        # "name": {"type"mock1",
        "make": {"type": "char", "data": "MockCo"},
        "model": {"type": "char", "data": "Mock1"},
        "description": {
            "type": "char",
            "data": "Simulates a meterological type of sensor for the purposes of testing. Data records are emitted once per second.",
        },
        "tags": {"type": "char", "data": "testing, mock, meteorology, sensor"},
        "format_version": {"type": "char", "data": "1.0.0"},
    },
    "variables": {
        "time": {
            "type": "str",
            "shape": ["time"],
            "attributes": {"long_name": {"type": "char", "data": "Time"}},
        },
        "temperature": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Temperature"},
                "units": {"type": "char", "data": "degree_C"},
            },
        },
        "rh": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "RH"},
                "units": {"type": "char", "data": "percent"},
            },
        },
        "pressure": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Pressure"},
                "units": {"type": "char", "data": "hPa"},
            },
        },
        "wind_speed": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Wind Speed"},
                "units": {"type": "char", "data": "m s-1"},
            },
        },
        "wind_direction": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Wind Direction"},
                "units": {"type": "char", "data": "degree"},
                "valid_min": {"type": "float", "data": 0.0},
                "valid_max": {"type": "float", "data": 360.0},
            },
        },
        "flow_rate": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Flow Rate"},
                "units": {"type": "char", "data": "l min-1"},
                "valid_min": {"type": "float", "data": 0.0},
                "valid_max": {"type": "float", "data": 5.0},
            },
        },
    },
    "settings": {
        "flow_rate": {
            "type": "float",
            "shape": ["time"],
            "attributes": {
                "long_name": {"type": "char", "data": "Flow Rate"},
                "units": {"type": "char", "data": "l min-1"},
                "valid_min": {"type": "float", "data": 0.0},
                "valid_max": {"type": "float", "data": 5.0},
            },
        },
    },
}


class SensorAttribute(BaseModel):
    # name: str
    type: str | None = "str"
    data: Any

    @validator("data")
    def data_check(cls, v, values):
        if "type" in values:
            data_type = values["type"]
            if data_type == "char":
                data_type = "str"
                
            if "type" in values and not isinstance(v, eval(data_type)):
                raise ValueError("attribute data is wrong type")
        return v

class SensorVariable(BaseModel):
    """docstring for SensorVariable."""

    # name: str
    type: str | None = "str"
    shape: list[str] | None = ["time"]
    attributes: dict[str, SensorAttribute]
    # attributes: dict | None = dict()
    # modes: list[str] | None = ["default"]

class SensorSetting(BaseModel):
    """docstring for SensorSetting."""

    # name: str
    type: str | None = "str"
    shape: list[str] | None = ["time"]
    attributes: dict[str, SensorAttribute]
    # attributes: dict | None = dict()
    # modes: list[str] | None = ["default"]

class SensorMetadata(BaseModel):
    """docstring for SensorMetadata."""
    attributes: dict[str, SensorAttribute]
    variables: dict[str, SensorVariable]
    settings: dict[str, SensorSetting]

class SensorConfig(BaseModel):
    """docstring for SensorConfig."""

    make: str
    model: str
    serial_number: str
    metadata: SensorMetadata
    # # variables: list | None = []
    # attributes: dict[str, SensorAttribute]
    # variables: dict[str, SensorVariable]
    # # # variables: dict | None = {}
    # settings: dict[str, SensorSetting]
    interfaces: dict | None = {}
    daq: str | None = "default"


def configure():

    # attributes
    attributes = dict()
    # for name, att in metadata["attributes"]:

    meta = SensorMetadata(
        attributes=metadata["attributes"],
        variables=metadata["variables"],
        settings=metadata["settings"]
    )

    config = SensorConfig(
        make=metadata["attributes"]["make"]["data"],
        model=metadata["attributes"]["model"]["data"],
        serial_number="1234",
        metadata=meta
        # attributes=metadata["attributes"],
        # variables=metadata["variables"],
        # settings=metadata["settings"]
    )    

    # print(json.dumps(config.metadata.dict(), indent=3))
    # if "time" in config.metadata.variables:
    #     print(config.metadata.dict(include={"attributes"}))
    print(config.metadata.attributes["format_version"].data)

if __name__ == "__main__":

    configure()