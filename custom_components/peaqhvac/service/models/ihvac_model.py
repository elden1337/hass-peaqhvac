from dataclasses import dataclass, field


@dataclass
class IHvacModel:
    current_offset: int = 0
    current_offset_dict: dict = field(default_factory=lambda: {})
    current_offset_dict_tomorrow: dict = field(default_factory=lambda: {})
    current_offset_dict_combined: dict = field(default_factory=lambda: {})

    listenerentities: list = field(default_factory=lambda: [])

