from dataclasses import dataclass, field


@dataclass
class ClusterData:
    max_price: float = 0
    min_price: float = 0
    avg_price: float = 0
    hours: list = field(default_factory=lambda: [])
    hours_ranked: list = field(default_factory=lambda: [])  # lower index is means cheaper
