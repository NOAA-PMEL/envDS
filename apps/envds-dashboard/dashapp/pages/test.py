x = {
    "database": "registry",
    "collection": "sensor_definition",
    "operation-type": "insert",
    "data": {
        "_id": "KippZonen: :SPLite2: :v1",
        "attributes": {
            "make": {"type": "string", "data": "KippZonen"},
            "model": {"type": "string", "data": "SPLite2"},
            "description": {"type": "string", "data": "Pyranometer"},
            "tags": {"type": "char", "data": "met, temperature, rh, sensor"},
            "format_version": {"data": "1.0.0"},
            "serial_number": {"type": "string", "data": None},
        },
        "dimensions": {"time": None},
        "make": "KippZonen",
        "model": "SPLite2",
        "variables": {
            "time": {
                "type": "str",
                "shape": ["time"],
                "attributes": {"long_name": {"type": "string", "data": "Time"}},
            },
            "volts": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {"type": "char", "data": "Measured voltage"},
                    "units": {"type": "char", "data": "volts"},
                },
            },
            "sensitivity": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Sensitivity of sensor (uV / W*m2)",
                    },
                    "units": {"type": "char", "data": "uV W-1 m2"},
                },
            },
            "irradiance": {
                "type": "float",
                "shape": ["time"],
                "attributes": {
                    "long_name": {
                        "type": "char",
                        "data": "Irradiance of sensor (uV / W*m2)",
                    },
                    "units": {"type": "char", "data": "W m-2"},
                },
            },
        },
        "version": "v1",
    },
}
