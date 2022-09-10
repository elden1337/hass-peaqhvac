from homeassistant.core import HomeAssistant
from custom_components.peaqhvac.const import DOMAIN

class Sensors:
    peaqenabled: bool
    temp_trend_outdoors: float
    temp_trend_indoors: float
    prognosis: str
    set_temp_indoors: float #input-numbersensor
    #temp_sensors_indoor: list[float]
    #temp_sensors_outdoor: list[float]

    #these two are siblings. demandEnum as state
    # waterheatersensor
    # hvacsensor

    # avgtempsensor (with max and min as attributes, based on the list of tempsensors from config)

    def set_sensors_from_list(self, inputstr: str) -> None:
        input_list = []

        try:
            input_list = inputstr.split(',')
        except:
            pass

        if len(input_list) > 0:
            for i in input_list:
                self._set_single_sensor(i)

    def _set_single_sensor(self, sensor: str):
        pass


class Hub:
    hub_id = 1338

    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self.sensors = Sensors()

    async def call_enable_peaq(self):
        pass

    async def call_disable_peaq(self):
        pass