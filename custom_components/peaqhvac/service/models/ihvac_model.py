from dataclasses import dataclass, field


@dataclass
class IHvacModel:
    current_offset: int = 0
    hvac_dm: int | None = None
    raw_offset: int = 0


