import logging

_LOGGER = logging.getLogger(__name__)

def nametoid(input_string) -> str:
    if isinstance(input_string, str):
        return input_string.lower().replace(" ", "_").replace(",", "")
    return input_string

def try_parse(input_string:str, parsetype:type):
    try:
        ret = parsetype(input_string)
        return ret
    except Exception as e:
        return False

def subtract(*args):
    if len(args) == 1:
        return args[0]
    return args[0] - sum(args[1:])

def parse_to_type(value, _type):
    if isinstance(value, _type):
        return value
    elif _type is float:
        try:
            return float(value)
        except ValueError:
            return 0
    elif _type is int:
        try:
            return int(float(value))
        except ValueError:
            return 0
    elif _type is bool:
        try:
            if value is None:
                return False
            elif value.lower() == "on":
                return True
            elif value.lower() == "off":
                return False
        except ValueError as e:
            msg = f"Could not parse bool, setting to false to be sure {value}, {e}"
            _LOGGER.error(msg)
            return False
    elif _type is str:
        return str(value)