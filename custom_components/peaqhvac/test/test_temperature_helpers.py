import pytest

from ..service.hub.target_temp import adjusted_tolerances
from ..service.hvac.house_heater.temperature_helper import get_temp_extremas

MINTOLERANCE = 0.2
MAXTOLERANCE = 0.5

def _current_tolerances(determinator: bool, current_offset: int, adjust_tolerances: bool = True) -> float:
    if adjust_tolerances:
        tolerances= adjusted_tolerances(current_offset, MINTOLERANCE, MAXTOLERANCE)
    else:
        tolerances = MINTOLERANCE, MAXTOLERANCE
    return tolerances[0] if (determinator > 0 or determinator is True) else tolerances[1]

def test_temp_extremas_one_positive():
    ter = get_temp_extremas(0, [0, 0, 0, 0, 1, 0, 0, 0, 0], _current_tolerances)
    assert ter == 0.8

def test_temp_extremas_one_negative():
    ter = get_temp_extremas(0, [0, 0, 0, 0, -1, 0, 0, 0, 0], _current_tolerances)
    assert ter == -0.5