import logging
from datetime import datetime, timedelta
from statistics import mean, stdev

from custom_components.peaqhvac.service.models.enums.hvac_presets import \
    HvacPresets

_LOGGER = logging.getLogger(__name__)

TODAY = "today"
TOMORROW = "tomorrow"

def offset_per_day(
    day_values: dict,
    tolerance: int | None,
    indoors_preset: HvacPresets = HvacPresets.Normal,
) -> list:
    ret = {}
    if tolerance is not None:
        for k, v in day_values.items():
            ret[k] = int(round((day_values[k] *tolerance) * -1, 0))
            if indoors_preset is HvacPresets.Away:
                ret[k] -= 1
    return list(ret.values())

# def offset_per_day(
#     day_values: dict,
#     tolerance: int | None,
#     indoors_preset: HvacPresets = HvacPresets.Normal,
# ) -> list:
#     ret = {}
#     _max_today = max(day_values.values(), default=0)
#     _min_today = min(day_values.values(), default=0)
#     if tolerance is not None and _max_today != _min_today:
#         try:
#             factor = max(abs(_max_today), abs(_min_today)) / tolerance
#         except ZeroDivisionError:
#             _LOGGER.info(
#                 f"Offset calculation not finalized due to missing tolerance. Will change shortly..."
#             )
#             factor = 1
#         for k, v in day_values.items():
#             ret[k] = int(round((day_values[k] / factor) * -1, 0))
#             if indoors_preset is HvacPresets.Away:
#                 ret[k] -= 1
#     return list(ret.values())


def get_offset_dict(offset_dict, dt_now) -> dict:
    return {
        TODAY:    offset_dict.get(dt_now.date(), {}),
        TOMORROW: offset_dict.get(dt_now.date() + timedelta(days=1), {}),
    }


def set_offset_dict(prices: list[float], dt: datetime, min_price: float, existing: dict) -> dict:
    ret = {}
    dt = dt.replace(minute=0, second=0, microsecond=0)
    dt_date = dt.date()
    all_offsets = _deviation_from_mean(prices, min_price, dt)
    if all([
        len(existing.get(dt_date, {})),
        not len([k.hour for k,v in all_offsets.items() if k.date() ==dt_date + timedelta(days=1)])
        ]):
        ret[dt_date] = existing[dt_date]
    else:
        ret[dt_date] = {k.hour: v for k, v in all_offsets.items() if k.date() == dt_date}
    ret[dt_date + timedelta(days=1)] = {k.hour: v for k, v in all_offsets.items() if k.date() == dt_date + timedelta(days=1)}
    return ret


def _get_timedelta(prices: list[float]) -> int:
    _len = len(prices)
    match _len:
        case 23 | 24 | 25 | 47 | 48 | 49:
            return 60
        case 92 | 96 | 100 | 188 | 192 | 196:
            return 15


def _deviation_from_mean(prices: list[float], min_price: float, dt: datetime) -> dict[datetime, float]:
    if not len(prices):
        return {}
    delta = _get_timedelta(prices)
    dt_lister = dt.replace(hour=0)

    avg = mean(prices)
    devi = stdev(prices)

    if dt.hour >= 13:
        avg2 = mean(prices[13:])
        devi2 = stdev(prices[13:])

    deviation_dict = {}
    for i, num in enumerate(prices):
        _devi = devi if i < 13 else devi2
        _avg = avg if i < 13 else avg2
        deviation = (num - _avg) / _devi
        if _devi < 1:
            deviation *= 0.5
        setval = 0

        if num <= min_price:
            setval = min(round(deviation, 2), 0)
        elif num <= min_price * 2:
            setval = deviation - 1 if deviation > 1 else deviation
            setval = round(setval, 2)
        else:
            setval = round(deviation, 2)
        deviation_dict[dt_lister + timedelta(minutes=delta * i)] = setval
    return deviation_dict


def max_price_lower_internal(tempdiff: float, peaks_today: list) -> bool:
    """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
    if tempdiff >= 0:
        if datetime.now().hour in peaks_today:
            return True
        elif datetime.now().hour < 23 and datetime.now().minute > 40:
            if datetime.now().hour + 1 in peaks_today:
                return True
    return False
