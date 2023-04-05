from typing import Tuple
import statistics


def identify_peaks(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if p < statistics.mean(prices):
            continue
        if idx == 0 or idx == len(prices) - 1:
            if p == max(prices):
                ret.append(idx)
        else:
            if all([
                _check_deviation_peaks(p, prices[idx - 1]),
                _check_deviation_peaks(p, prices[idx + 1])
            ]):
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
            if all([
                _check_deviation_valleys(p, prices[idx - 1]),
                _check_deviation_valleys(p, prices[idx + 1])
            ]):
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
            if all([
                prices[idx] < prices[idx - 1],
                prices[idx] < prices[idx + 1],
                min(prices[idx - 1], prices[idx + 1]) / max(prices[idx - 1], prices[idx + 1]) > 0.8
            ]):
                ret.append(idx)
    return ret


def _find_single_anomalies(
        adj: list
) -> list[int]:
    for idx, p in enumerate(adj):
        if idx <= 1 or idx >= len(adj) - 1:
            pass
        else:
            if all([
                adj[idx - 1] == adj[idx + 1],
                adj[idx - 1] != adj[idx]
            ]):
                _prev = adj[idx - 1]
                _curr = adj[idx]
                diff = max(_prev, _curr) - min(_prev, _curr)
                if int(diff / 2) > 0:
                    if _prev > _curr:
                        adj[idx] += int(diff / 2)
                    else:
                        adj[idx] -= int(diff / 2)
    return adj


def _smooth_upwards_transitions(start_list, tolerance):
    for idx, v in enumerate(start_list):
        if idx < len(start_list) - 1:
            if start_list[idx + 1] >= start_list[idx] + tolerance:
                start_list[idx] += 1
    return start_list


def smooth_transitions(
        today: list,
        tomorrow: list,
        tolerance: int
) -> Tuple[dict, dict]:
    if tolerance is not None:
        tolerance = min(tolerance, 3)   
    else:
        tolerance = 3

    start_list: list = []
    ret: Tuple[dict, dict] = {}, {}

    start_list.extend(today)
    if 23 <= len(tomorrow) <= 25:
        start_list.extend(tomorrow)
    if len(start_list) < 24:
        return ret
    
    start_list = _find_single_anomalies(start_list)
    start_list = _smooth_upwards_transitions(start_list, tolerance)

    for hour in range(0, 24):
        ret[0][hour] = start_list[hour]
    if 23 <= len(tomorrow) <= 25:
        for hour in range(24, min(len(tomorrow) + 24, 48)):
            ret[1][hour - 24] = start_list[hour]
    return ret
