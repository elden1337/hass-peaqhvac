from statistics import mean
from math import floor
import logging

_LOGGER = logging.getLogger(__name__)


def get_tempdiff_inverted(current_offset: int, temp_diff: float, determine_tolerance: callable) -> int:
    diff = temp_diff + 0.00001
    if abs(diff) < 0.2:
        return 0
    """get the inverted tolerance in this case"""
    _tolerance = determine_tolerance(diff * -1, current_offset)
    ret = floor(abs(diff) / _tolerance) * -1
    if diff > 0:
        return ret
    return ret * -1


def get_temp_extremas(current_offset: int, all_temps: list, determine_tolerance: callable) -> float:
    diffs = all_temps
    cold_diffs, hot_diffs = [d for d in diffs if d > 0] + [0], [d for d in diffs if d < 0] + [0]
    hot_large = abs(min(hot_diffs))
    cold_large = abs(max(cold_diffs))
    if hot_large == cold_large:
        return 0
    is_cold = cold_large > hot_large
    tolerance = determine_tolerance(is_cold, current_offset, False)
    if is_cold:
        ret = _temp_extremas_return(cold_diffs, tolerance)
        return ret / max(len(hot_diffs), 1)
    ret = _temp_extremas_return(hot_diffs, tolerance)
    return ret / max(len(cold_diffs), 1)


def get_temp_trend_offset(temp_trend_is_clean: bool, predicted_temp: float, adjusted_temp: float) -> float:
    if not temp_trend_is_clean:
        return 0
    new_temp_diff = round(predicted_temp - adjusted_temp, 3)
    if abs(new_temp_diff) <= 0.1:
        return 0
    if predicted_temp >= adjusted_temp:
        ret = max(round(new_temp_diff, 1), 0)
    else:
        ret = min(round(new_temp_diff, 1), 0)
    return min((round(ret / 2, 1)), 1) * -1


def _temp_extremas_return(diffs, tolerance) -> float:
    avg_diff = max(diffs[:-1])
    dev = 1 if avg_diff >= 0 else -1
    ret = (abs(avg_diff) - tolerance) * dev
    ret = max(ret, 0) if dev == 1 else min(ret, 0)
    return round(ret, 2)
