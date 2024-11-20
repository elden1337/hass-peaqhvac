from statistics import mean
from math import floor
import logging

_LOGGER = logging.getLogger(__name__)

def get_tempdiff_inverted(current_offset: int, temp_diff: float, min_temp_diff: float, determine_tolerance: callable) -> int:
    
    def calc_int(diff: float) -> int:
        diff += 0.00001
        if abs(diff) < 0.2:
            return 0
        _tolerance = determine_tolerance(diff * -1, current_offset)
        return floor(abs(diff) / _tolerance) * (-1 if diff > 0 else 1)

    ret = calc_int(temp_diff)
    min_ret = calc_int(min_temp_diff * 0.4 if min_temp_diff < 0 else 0)
    combined_ret = ret + min_ret

    if abs(combined_ret) < 0.2:
        return 0

    return combined_ret


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


