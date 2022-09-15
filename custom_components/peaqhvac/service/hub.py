from homeassistant.core import HomeAssistant
from custom_components.peaqhvac.const import DOMAIN
from peaqevcore.models.hub.hubmember import HubMember
from custom_components.peaqhvac.service.models.config_model import ConfigModel


class Sensors:
    peaqenabled: HubMember
    temp_trend_outdoors: float
    temp_trend_indoors: float
    prognosis: str
    set_temp_indoors: float #input-numbersensor
    temp_sensors_indoor: list[str]  #list of entities, not a value
    temp_sensors_outdoor: list[str] #list of entities, not a value

    #these two are siblings. demandEnum as state
    # waterheatersensor
    # hvacsensor

    # avgtempsensor (with max and min as attributes, based on the list of tempsensors from config)

class Hub:
    hub_id = 1338

    def __init__(self, hass: HomeAssistant, hub_options: ConfigModel):
        self.options = hub_options
        self._hass = hass
        self.sensors = Sensors()
        self.sensors.temp_sensors_outdoor = self.options.outdoor_tempsensors
        self.sensors.temp_sensors_indoor = self.options.indoor_tempsensors

    async def call_enable_peaq(self):
        pass

    async def call_disable_peaq(self):
        pass