import pytest

from ..service.hub.target_temp import adjusted_tolerances
from ..service.hvac.house_heater.temperature_helper import get_temp_extremas, get_tempdiff_inverted

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


def test_tempdiff_cold():
    tempdiff = -0.5
    ret1 = get_tempdiff_inverted(0, tempdiff, _current_tolerances)
    assert ret1 == 2
    ret2 = get_tempdiff_inverted(-1, tempdiff, _current_tolerances)
    assert ret2 == 2
    ret3 = get_tempdiff_inverted(-2, tempdiff, _current_tolerances)
    assert ret3 == 2
    ret4 = get_tempdiff_inverted(-3, tempdiff, _current_tolerances)
    assert ret4 == 2

def test_tempdiff_hot():
    tempdiff = 0.5
    ret1 = get_tempdiff_inverted(0, tempdiff, _current_tolerances)
    assert ret1 == -1
    ret2 = get_tempdiff_inverted(-1, tempdiff, _current_tolerances)
    assert ret2 == -1
    ret3 = get_tempdiff_inverted(-2, tempdiff, _current_tolerances)
    assert ret3 == -1
    ret4 = get_tempdiff_inverted(-3, tempdiff, _current_tolerances)
    assert ret4 == -1