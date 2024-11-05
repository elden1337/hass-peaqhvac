from datetime import datetime
from dataclasses import dataclass, field
from custom_components.peaqhvac.service.models.enums.hvac_presets import HvacPresets

@dataclass
class WaterBoostData:
    min_price: float = None  # type: ignore
    non_hours_raw: list[int] = field(default_factory=lambda: [], repr=False, compare=False)
    demand_hours_raw: list[int] = field(default_factory=lambda: [], repr=False, compare=False)
    initialized: bool = False
    price_dict: dict = field(default_factory=lambda: {})
    preset: HvacPresets = HvacPresets.Normal
    now_dt: datetime = None  # type: ignore
    latest_boost: datetime = None  # type: ignore
    temp_trend: float = -0.5  # type: ignore
    current_temp: float = None  # type: ignore
    target_temp: float = None  # type: ignore
    floating_mean: float = field(default=None, init=False)
    non_hours: set = field(default_factory=lambda: [], init=False)
    demand_hours: set = field(default_factory=lambda: {}, init=False)
    latest_calculation: datetime | None = field(default=None, init=False)
    latest_override_demand: int = field(default=None, init=False)
    should_update: bool = field(default=True, init=False)

    def __post_init__(self):
        self.now_dt = datetime.now() if self.now_dt is None else self.now_dt
        self.latest_boost = self.now_dt if self.latest_boost is None else self.latest_boost
        self.min_price = -float('inf') if self.min_price is None else self.min_price