import logging
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets

_LOGGER = logging.getLogger(__name__)


def offset_per_day(
          day_values: dict, 
          tolerance: int|None, 
          indoors_preset: HvacPresets = HvacPresets.Normal
          ) -> list:
        ret = {}
        _max_today = max(day_values.values())
        _min_today = min(day_values.values())
        if tolerance is not None:
            try:
                factor = max(abs(_max_today), abs(_min_today)) / tolerance
            except ZeroDivisionError as z:
                _LOGGER.info(f"Offset calculation not finalized due to missing tolerance. Will change shortly...")
                factor = 1
            for k, v in day_values.items():
                ret[k] = int(round((day_values[k] / factor) * -1, 0))
                if indoors_preset is HvacPresets.Away:
                    ret[k] -= 1
        return ret.values()