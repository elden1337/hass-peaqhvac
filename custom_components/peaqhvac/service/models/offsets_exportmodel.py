from typing import Tuple, List, Dict
from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class OffsetsExportModel:
    peaks: Tuple[List, List]
    _raw_offsets: List[int] = field(default_factory=list)
    _current_offset: List[int] = field(default_factory=list)
    _current_offset_tomorrow: List[int] = field(default_factory=list)

    @property
    def raw_offsets(self) -> List[int]:
        """Returns the raw offsets list."""
        return self._raw_offsets

    @raw_offsets.setter
    def raw_offsets(self, val: Dict) -> None:
        """Sets the raw offsets list from a dictionary."""
        self._raw_offsets = self._offset_dict_to_list(val)

    @property
    def current_raw_offset(self) -> int:
        """Returns the current raw offset based on the current hour."""
        if not self._raw_offsets:
            return 0
        return self._raw_offsets[datetime.now().hour]

    @property
    def current_offset(self) -> List[int]:
        """Returns the current offset list."""
        return self._current_offset

    @current_offset.setter
    def current_offset(self, val: Dict) -> None:
        """Sets the current offset list from a dictionary."""
        self._current_offset = self._offset_dict_to_list(val)

    @property
    def current_offset_tomorrow(self) -> List[int]:
        """Returns the current offset list for tomorrow."""
        return self._current_offset_tomorrow

    @current_offset_tomorrow.setter
    def current_offset_tomorrow(self, val: Dict) -> None:
        """Sets the current offset list for tomorrow from a dictionary."""
        self._current_offset_tomorrow = self._offset_dict_to_list(val)

    @staticmethod
    def _offset_dict_to_list(input: Dict) -> List[int]:
        """Converts a dictionary of offsets to a list."""
        return list(input.values())