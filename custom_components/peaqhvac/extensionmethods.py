import logging
import time
from functools import partial
import inspect

_LOGGER = logging.getLogger(__name__)


def nametoid(input_string) -> str:
    if isinstance(input_string, str):
        return input_string.lower().replace(" ", "_").replace(",", "")
    return input_string


def try_parse(input_string: str, parsetype: type):
    try:
        ret = parsetype(input_string)
        return ret
    except Exception:
        return False


def subtract(*args):
    if len(args) == 1:
        return args[0]
    return args[0] - sum(args[1:])


def parse_to_type(value, _type):
    match _type:
        case t if t is float:
            try:
                return float(value)
            except ValueError:
                return 0
        case t if t is int:
            try:
                return int(float(value))
            except ValueError:
                return 0
        case t if t is bool:
            return _parse_to_type_bool(value)
        case t if t is str:
            return str(value)
        case _:
            if isinstance(value, _type):
                return value
            raise TypeError(f"Could not parse {value} to {_type}")


def _parse_to_type_bool(value) -> bool:
    try:
        if value is None:
            return False
        if value.lower() == "on":
            return True
        if value.lower() == "off":
            return False
    except ValueError as e:
        msg = f"Could not parse bool, setting to false to be sure {value}, {e}"
        _LOGGER.error(msg)
        return False


def dt_from_epoch(epoch: int) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(epoch))


async def async_iscoroutine(object):
    while isinstance(object, partial):
        object = object.func
    return inspect.iscoroutinefunction(object)
