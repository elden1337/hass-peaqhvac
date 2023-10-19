from dataclasses import dataclass
from typing import Tuple

@dataclass
class OffsetsModel:
    calculated_offsets: Tuple[dict, dict]
    raw_offsets: Tuple[dict, dict]