import logging
from datetime import datetime

from custom_components.peaqhvac.service.models.enums.hvac_presets import \
    HvacPresets

_LOGGER = logging.getLogger(__name__)


def offset_per_day(
    day_values: dict,
    tolerance: int | None,
    indoors_preset: HvacPresets = HvacPresets.Normal,
) -> list:
    ret = {}
    _max_today = max(day_values.values())
    _min_today = min(day_values.values())
    if tolerance is not None:
        try:
            factor = max(abs(_max_today), abs(_min_today)) / tolerance
        except ZeroDivisionError:
            _LOGGER.info(
                f"Offset calculation not finalized due to missing tolerance. Will change shortly..."
            )
            factor = 1
        for k, v in day_values.items():
            ret[k] = int(round((day_values[k] / factor) * -1, 0))
            if indoors_preset is HvacPresets.Away:
                ret[k] -= 1
    return ret.values()


def max_price_lower_internal(tempdiff: float, peaks_today: list) -> bool:
    """Temporarily lower to -10 if this hour is a peak for today and temp > set-temp + 0.5C"""
    if tempdiff >= 0:
        if datetime.now().hour in peaks_today:
            return True
        elif datetime.now().hour < 23 and datetime.now().minute > 40:
            if datetime.now().hour + 1 in peaks_today:
                return True
    return False
