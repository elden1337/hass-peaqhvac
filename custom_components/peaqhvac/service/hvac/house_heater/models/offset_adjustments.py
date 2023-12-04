from enum import Enum

class OffsetAdjustments(Enum):
    TemporarilyLowerOffset = 0
    PeakHour = 1
    KeepCompressorRunning = 2
    LowerOffsetStrong = 3
