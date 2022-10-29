from datetime import datetime
from statistics import stdev, mean
from custom_components.peaqhvac.service.models.clusterdata import ClusterData


class Cluster:
    def __init__(self):
        self._clusters = {}
        self._cluster_data = {}
        self._prices = []

    @property
    def prices(self):
        return self._prices

    @prices.setter
    def prices(self, lst):
        self._prices = lst
        self.find_areas()

    @property
    def clusters(self):
        return self._clusters

    @clusters.setter
    def clusters(self, val):
        self._clusters = val
        self.set_cluster_data()

    @property
    def current_cluster(self):
        try:
            return self._clusters[datetime.now().hour]
        except:
            return None

    def cluster_data(self, cluster_index) -> ClusterData:
        return self._cluster_data[cluster_index]

    def find_areas(self):
        _p = self.prices
        deviation = stdev(_p)
        clusters = {}
        current_cluster = 0
        for index, p in enumerate(_p):
            if index == len(_p) - 1:
                break
            _next = _p[index + 1]
            if stdev([p, _next]) > deviation:
                if not index in clusters.keys():
                    clusters[index] = current_cluster
                    current_cluster += 1
                clusters[index + 1] = clusters[index]
            else:
                clusters[index] = current_cluster
        self.clusters = clusters

    def set_cluster_data(self):
        ret = {}
        for c in set(self.clusters.values()):
            _hours = [i for i in self.clusters if self.clusters[i] == c]
            _localized_prices = [p for idx, p in enumerate(self.prices) if idx in _hours]
            ret[c] = ClusterData(
                max_price=max(_localized_prices),
                min_price=min(_localized_prices),
                avg_price=round(mean(_localized_prices), 2),
                hours=_hours,
                hours_ranked=Cluster._rank_hours(_localized_prices, _hours)
            )
        self._cluster_data = ret

    @staticmethod
    def _rank_hours(prices, hours) -> list:
        res = {hours[i]: prices[i] for i in range(len(hours))}
        return [k for k, v in sorted(res.items(), key=lambda item: item[1])]


# prices = [0.869, 0.749, 0.591, 0.478, 0.464, 0.539, 0.756, 1.249, 1.366, 1.199, 0.97, 0.972, 0.865, 0.812, 0.835, 0.892,
#           0.836, 1.648, 1.671, 1.061, 0.851, 0.758, 0.526, 0.372]
# c = Cluster()
# c.prices = prices
# cc = c.current_cluster
# ff = c.cluster_data(cc)
# print(ff.avg_price)
# print(ff.hours)
# print(ff.max_price)
# print(ff.min_price)
# print(ff.hours_ranked)