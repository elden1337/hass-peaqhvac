import pytest

from ..service.hub.target_temp import adjusted_tolerances
from ..service.hvac.house_heater.temperature_helper import get_tempdiff_inverted, get_temp_trend_offset

MINTOLERANCE = 0.2
MAXTOLERANCE = 0.5

def _current_tolerances(determinator: bool, current_offset: int, adjust_tolerances: bool = True) -> float:
    if adjust_tolerances:
        tolerances= adjusted_tolerances(current_offset, MINTOLERANCE, MAXTOLERANCE)
    else:
        tolerances = MINTOLERANCE, MAXTOLERANCE
    return tolerances[0] if (determinator > 0 or determinator is True) else tolerances[1]


def test_tempdiff_one_room_cold():
    tempdiff = 0.5
    ret1 = get_tempdiff_inverted(0, tempdiff, 0, _current_tolerances)
    assert ret1 == -1
    ret2 = get_tempdiff_inverted(0, tempdiff, -1.5, _current_tolerances)
    assert ret2 == 1


def test_tempdiff_cold():
    tempdiff = -0.5
    ret1 = get_tempdiff_inverted(0, tempdiff,0, _current_tolerances)
    assert ret1 == 2
    ret2 = get_tempdiff_inverted(-1, tempdiff, 0,_current_tolerances)
    assert ret2 == 2
    ret3 = get_tempdiff_inverted(-2, tempdiff, 0,_current_tolerances)
    assert ret3 == 2
    ret4 = get_tempdiff_inverted(-3, tempdiff, 0,_current_tolerances)
    assert ret4 == 2


def test_tempdiff_hot():
    tempdiff = 0.5
    ret1 = get_tempdiff_inverted(0, tempdiff,0, _current_tolerances)
    assert ret1 == -1
    ret2 = get_tempdiff_inverted(-1, tempdiff, 0,_current_tolerances)
    assert ret2 == -1
    ret3 = get_tempdiff_inverted(-2, tempdiff,0, _current_tolerances)
    assert ret3 == -1
    ret4 = get_tempdiff_inverted(-3, tempdiff,0, _current_tolerances)
    assert ret4 == -1


def test_temp_trend_offset_expected_colder_than_desired_with_diff_offset():
    for i in range(1, 10):
        ret = get_temp_trend_offset(True, i, 19.8, 20)
        assert ret == 0


def test_temp_trend_offset_expected_colder_than_desired_with_diff_neg_offset():
    for i in range(1, 10):
        ret = get_temp_trend_offset(True, i*-1, 19.8, 20)
        assert ret != 0


def test_temp_trend_offset_expected_warmer_than_desired_with_diff_offset():
    for i in range(1, 10):
        ret = get_temp_trend_offset(True, i, 20.8, 20)
        assert ret != 0


def test_temp_trend_offset_expected_warmer_than_desired_with_diff_neg_offset():
    for i in range(1, 10):
        ret = get_temp_trend_offset(True, i*-1, 20.8, 20)
        assert ret == 0


def test_too_cold_only_pos_trend():
    for i in range(1, 10):
        icheck = i*-1
        ret = get_temp_trend_offset(True, icheck, 19.5, 20)
        assert ret > 0 if icheck < 0 else ret < 0


def test_assert_too_hot_only_neg_trend():
    for i in range(1, 10):
        icheck = i
        ret = get_temp_trend_offset(True, icheck, 20.5, 20)
        assert ret > 0 if icheck < 0 else ret < 0

