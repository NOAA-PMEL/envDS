from datetime import datetime
import time
import math
import json

def time_to_next(sec: float) -> float:
    now = time.time()
    delta = sec - (math.fmod(now, sec))
    return delta

def get_datetime_format(fraction=True):
    isofmt = "%Y-%m-%dT%H:%M:%SZ"
    if fraction:
        isofmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    return isofmt

def get_datetime():
    return datetime.utcnow()

def get_datetime_string(fraction: bool=True):
    return datetime_to_string(get_datetime(), fraction=fraction)

def datetime_to_string(dt: datetime, fraction: bool=True):
    if dt:
        dt_string = dt.strftime(get_datetime_format(fraction=fraction))
        return dt_string
def string_to_datetime(dt_string: str, fraction: bool=True):
    if dt_string:
        try:
            isofmt = get_datetime_format(fraction=fraction)
            return datetime.strptime(dt_string, get_datetime_format())
        except ValueError:
            return None

def datetime_mod_sec(sec: int) -> int:
    return get_datetime().second % sec

def seconds_elapsed(inital_dt: datetime) -> float:
    delta = get_datetime() - inital_dt
    return delta.total_seconds()

def get_checksum(data: dict) -> int:
    return hash(json.dumps(data, sort_keys=True))