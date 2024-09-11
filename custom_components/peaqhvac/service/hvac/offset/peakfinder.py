import statistics
from datetime import timedelta
import logging

_LOGGER = logging.getLogger(__name__)


def identify_peaks(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if p < statistics.mean(prices):
            continue
        if idx == 0 or idx == len(prices) - 1:
            if p == max(prices):
                ret.append(idx)
        else:
            if all(
                    [
                        _check_deviation_peaks(p, prices[idx - 1]),
                        _check_deviation_peaks(p, prices[idx + 1]),
                    ]
            ):
                ret.append(idx)
    return ret


def identify_valleys(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if p > statistics.mean(prices):
            continue
        if idx == 0 or idx == len(prices) - 1:
            if p == min(prices):
                ret.append(idx)
        else:
            if all(
                    [
                        _check_deviation_valleys(p, prices[idx - 1]),
                        _check_deviation_valleys(p, prices[idx + 1]),
                    ]
            ):
                ret.append(idx)
    return ret


def _check_deviation_peaks(p: float, neighbor: float) -> bool:
    if any([neighbor == 0, p == 0]):
        neighbor += 0.01
        p += 0.01
    if p > neighbor:
        return neighbor / p < 0.9
    return False


def _check_deviation_valleys(p: float, neighbor: float) -> bool:
    if any([neighbor == 0, p == 0]):
        neighbor += 0.01
        p += 0.01
    if p < neighbor:
        return p / neighbor > 0.9
    return False


def find_single_valleys(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if idx <= 1 or idx >= len(prices) - 2:
            pass
        else:
            if all(
                    [
                        p < prices[idx - 1],
                        p < prices[idx + 1],
                        min(prices[idx - 1], prices[idx + 1])
                        / max(prices[idx - 1], prices[idx + 1])
                        > 0.8,
                    ]
            ):
                ret.append(idx)
    return ret


def _find_single_anomalies(adj: dict) -> dict:
    return adj
    # for k, v in adj.items():
    #     if all([k+timedelta(hours=-1) in adj.items, k+timedelta(hours=+1) in adj.items]):


def _smooth_upwards_transitions(start_list: dict, tolerance):
    for k in start_list.keys():
        if k + timedelta(hours=+1) in start_list.items():
            if start_list[k + timedelta(hours=1)] >= start_list[k] + tolerance:
                start_list[k] += 1
    return start_list


def smooth_transitions(vals: dict, tolerance: int) -> dict:
    if tolerance is not None:
        tolerance = min(tolerance, 3)
    else:
        tolerance = 3

    ret = _find_single_anomalies(vals)
    ret = _smooth_upwards_transitions(ret, tolerance)

    if any(h for h in ret.values() if abs(h) > 10):
        _LOGGER.warning("Offset values are out of range", ret, vals)
    return ret
