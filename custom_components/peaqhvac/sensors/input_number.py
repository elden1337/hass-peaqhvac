from custom_components.peaqhvac.sensors.sensorbase import SensorBase



class InputNumberSensor(SensorBase):
    def __init__(
            self,
            listenerentity:str,
            minval: float,
            maxval: float,
            step: float,
            initval: float
    ):
    pass