import logging
from datetime import datetime, timedelta
from statistics import mean, stdev

from custom_components.peaqhvac.service.hvac.house_heater.models.calculated_offset import (
    CalculatedOffsetModel,
)
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets

_LOGGER = logging.getLogger(__name__)

TODAY = "today"
TOMORROW = "tomorrow"


def flat_day_lower_tolerance(prices):
    if not len(prices):
        return 0
    try:
        deviator = (max(prices) - min(prices)) / mean(prices)
        if deviator > 0.95:
            return 0
        if deviator > 0.8:
            return 1
        if deviator > 0.7:
            return 2
    except Exception as e:
        _LOGGER.error(f"Error in flat_day_lower_tolerance: {e}")
    return 0


def offset_per_day(
    day_values: dict,
    all_prices: list[float],
    tolerance: int | None,
    indoors_preset: HvacPresets = HvacPresets.Normal,
) -> dict:
    ret = {}
    if tolerance is not None:
        tolerance -= flat_day_lower_tolerance(all_prices)
        print(f"Flat day lower tolerance: {flat_day_lower_tolerance(all_prices)}")
        for k, v in day_values.items():
            ret[k] = int(round((v * tolerance) * -1, 0))
            if indoors_preset is HvacPresets.Away:
                ret[k] -= 1
            if abs(ret[k]) > tolerance:
                ret[k] = tolerance if ret[k] > 0 else tolerance * -1
    return ret


def get_offset_dict(offset_dict, dt_now) -> dict:
    return {
        TODAY: offset_dict.get(dt_now.date(), {}),
        TOMORROW: offset_dict.get(dt_now.date() + timedelta(days=1), {}),
    }


def set_offset_dict(prices: list[float], dt: datetime, min_price: float) -> dict:
    dt = dt.replace(minute=0, second=0, microsecond=0)
    all_offsets = _deviation_from_mean(prices, min_price, dt)
    return all_offsets


def _get_timedelta(prices: list[float]) -> int:
    _len = len(prices)
    match _len:
        case 23 | 24 | 25 | 47 | 48 | 49:
            return 60
        case 92 | 96 | 100 | 188 | 192 | 196:
            return 15


def _deviation_from_mean(
    prices: list[float], min_price: float, dt: datetime
) -> dict[datetime, float]:
    if not len(prices):
        return {}
    delta = _get_timedelta(prices)
    standardized_prices = [(p - mean(prices)) / stdev(prices) for p in prices]
    avg = mean(standardized_prices)
    devi = stdev(standardized_prices)
    avg2 = avg
    devi2 = devi

    if dt.hour >= 13:
        avg2 = mean(standardized_prices[13:])
        devi2 = stdev(standardized_prices[13:])

    deviation_dict = {}

    for i, num in enumerate(standardized_prices):
        _devi = devi if i < 13 else devi2
        _avg = avg if i < 13 else avg2
        deviation = (num - _avg) / _devi
        if _devi < 1:
            deviation *= 0.5

        if num <= min_price:
            setval = min(round(deviation, 2), 0)
        elif num <= min_price * 2:
            setval = deviation - 1 if deviation > 1 else deviation
            setval = round(setval, 2)
        else:
            setval = round(deviation, 2)
        deviation_dict[dt.replace(hour=0) + timedelta(minutes=delta * i)] = setval
    return deviation_dict


def max_price_lower_internal(tempdiff: float, peaks_today: list) -> bool:
    """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
    if tempdiff >= 0.5:
        if datetime.now().hour in peaks_today:
            return True
        if datetime.now().hour < 23 and datetime.now().minute > 50:
            if datetime.now().hour + 1 in peaks_today:
                return True
    return False


def adjust_to_threshold(
    offsetdata: CalculatedOffsetModel, outdoors_value: int, tolerance: int
) -> int:
    adjustment = offsetdata.sum_values()
    if adjustment is None or outdoors_value > 17:
        return min(0, adjustment)
    _tolerance = 3 if tolerance is None else tolerance
    ret = (
        min(adjustment, _tolerance)
        if adjustment >= 0
        else max(adjustment, _tolerance * -1)
    )
    return int(round(ret, 0))
