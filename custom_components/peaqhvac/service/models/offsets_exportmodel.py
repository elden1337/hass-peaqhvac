from typing import Tuple
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class OffsetsExportModel:
    peaks: Tuple[list, list]
    _raw_offsets: list = field(default_factory=lambda: [])
    _current_offset: list = field(default_factory=lambda: [])
    _current_offset_tomorrow: list = field(default_factory=lambda: [])

    @property
    def raw_offsets(self) -> list:
        return self._raw_offsets

    @raw_offsets.setter
    def raw_offsets(self, val:dict) -> None:
        self._raw_offsets = self._offset_dict_to_list(val)

    @property
    def current_raw_offset(self) -> int:
        if len(self._raw_offsets) == 0:
            return 0
        return self._raw_offsets[datetime.now().hour]

    @property
    def current_offset(self) -> list:
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val:dict) -> None:
        self._current_offset = self._offset_dict_to_list(val)

    @property
    def current_offset_tomorrow(self) -> list:
        return self._current_offset_tomorrow

    @current_offset_tomorrow.setter
    def current_offset_tomorrow(self, val:dict) -> None:
        self._current_offset_tomorrow = self._offset_dict_to_list(val)

    @staticmethod
    def _offset_dict_to_list(input: dict) -> list:
        return [i for i in input.values()]