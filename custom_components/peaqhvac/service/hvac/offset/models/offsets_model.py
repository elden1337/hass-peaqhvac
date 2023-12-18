from dataclasses import dataclass
from typing import Tuple

@dataclass
class OffsetsModel:
    calculated_offsets: dict
    raw_offsets: dict