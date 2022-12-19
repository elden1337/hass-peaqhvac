from dataclasses import dataclass, field

@dataclass
class OffsetModel:
    peaks_today: list[int] = field(default_factory=lambda: [])
    calculated_offsets = {}, {}
    raw_offsets = {}, {}
    tolerance = 0
    prognosis = None