from peaqevcore.models.hub.hubmember import HubMember
from custom_components.peaqhvac.service.hub.average import Average
from custom_components.peaqhvac.service.hub.trend import Gradient
from custom_components.peaqhvac.service.models.config_model import ConfigModel


class HubSensors:
    peaq_enabled: HubMember
    away_mode: HubMember
    temp_trend_outdoors: Gradient
    temp_trend_indoors: Gradient
    #prognosis: str
    set_temp_indoors: float #input-numbersensor
    average_temp_indoors: Average
    average_temp_outdoors: Average
    hvac_tolerance: int
    peaqev_installed: bool

    def __init__(self, options: ConfigModel, peaqev_discovered: bool = False):
        self.peaq_enabled = HubMember(initval=options.misc_options.enabled_on_boot, data_type=bool)
        self.away_mode = HubMember(initval=False, data_type=bool)
        self.hvac_tolerance = options.hvac_tolerance
        self.average_temp_indoors = Average(entities=options.indoor_tempsensors)
        self.average_temp_outdoors = Average(entities=options.outdoor_tempsensors)
        self.temp_trend_indoors = Gradient(max_samples=20, max_age=7200)
        self.temp_trend_outdoors = Gradient(max_samples=20, max_age=7200)
        self.set_temp_indoors = 20 #todo: fix this to input number

        if peaqev_discovered:
            self.peaqev_installed = True
        else:
            self.peaqev_installed = False

