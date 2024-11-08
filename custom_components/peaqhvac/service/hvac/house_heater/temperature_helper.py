from statistics import mean
from math import floor
import logging

_LOGGER = logging.getLogger(__name__)


def get_tempdiff_inverted(current_offset: int, temp_diff: float, min_temp_diff: float, determine_tolerance: callable) -> int:
    diff = temp_diff + 0.00001
    min_diff_influence = min_temp_diff * 0.5 if min_temp_diff < 0 else 0
    combined_diff = diff + min_diff_influence

    if abs(combined_diff) < 0.2:
        return 0

    _tolerance = determine_tolerance(combined_diff * -1, current_offset)
    ret = floor(abs(combined_diff) / _tolerance) * -1

    if combined_diff > 0:
        return ret
    return ret * -1


def get_temp_trend_offset(do_calc: bool, temp_diff_offset: float, predicted_temp: float, adjusted_temp: float) -> float:
    ret = 0
    if not do_calc:
        return ret

    new_temp_diff = round(predicted_temp - adjusted_temp, 3)

    if abs(new_temp_diff) <= 0.1:
        return ret

    # Protect against overcompensating
    if temp_diff_offset > 0:
        if predicted_temp < adjusted_temp:
            return ret
    elif temp_diff_offset < 0:
        if predicted_temp > adjusted_temp:
            return ret

    trend_factor = 1
    if abs(temp_diff_offset) > 1:
        trend_factor = min(1 + (abs(temp_diff_offset) - 1) * 0.3, 3.0)

    if predicted_temp >= adjusted_temp:
        ret = max(round(new_temp_diff * trend_factor, 1), 0)
        print(f"Positive Adjustment: {ret} (Trend Factor: {trend_factor})")
    else:
        ret = min(round(new_temp_diff * trend_factor, 1), 0)
        print(f"Negative Adjustment: {ret} (Trend Factor: {trend_factor})")

    # Apply a softer correction when the offset is already significant to avoid overcompensation
    ret = round(ret/2,1)
    ret = min(ret, 1.0)
    return ret * -1


