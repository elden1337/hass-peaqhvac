
def identify_peaks(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if idx == 0 or idx == len(prices) -1:
            if p == max(prices):
                ret.append(idx)
        else:
            if all([
                _check_deviation(p, prices[idx-1]),
                _check_deviation(p, prices[idx+1])
            ]):
                ret.append(idx)
    return ret

def _check_deviation(p: float, neighbor: float) -> bool:
    if p > neighbor:
        return neighbor / p > 0.8
    return False


def find_single_valleys(prices: list) -> list[int]:
    ret = []
    for idx, p in enumerate(prices):
        if idx <= 1 or idx >= len(prices) - 2:
            pass
        else:
            if all([
                prices[idx] < prices[idx-1],
                prices[idx] < prices[idx+1],
                min(prices[idx-1], prices[idx+1])/max(prices[idx-1], prices[idx+1]) > 0.8
            ]):
                ret.append(idx)
    return ret