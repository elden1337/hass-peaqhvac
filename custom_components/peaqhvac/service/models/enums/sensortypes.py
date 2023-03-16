from enum import Enum

class SensorType(Enum):
    DegreeMinutes = 1
    WaterTemp = 2
    Offset = 3
    ElectricalAddition = 4
    CompressorFrequency = 5
    HvacMode = 6
    DMCompressorStart = 7
    HvacTemp = 8
    CondenserReturn = 9
    FanSpeed = 10