from peaqevcore.models.hub.hubmember import HubMember

from custom_components.peaqhvac.service.hub.average import Average
from custom_components.peaqhvac.service.hub.target_temp import TargetTemp
from peaqevcore.common.trend import Gradient
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.peaqev_facade import PeaqevFacade


class HubSensors:
    peaq_enabled: HubMember
    temp_trend_outdoors: Gradient
    temp_trend_indoors: Gradient
    set_temp_indoors: TargetTemp
    average_temp_indoors: Average
    average_temp_outdoors: Average
    hvac_tolerance: int
    peaqev_installed: bool
    peaqev_facade: PeaqevFacade

    def __init__(
        self, hub, options: ConfigModel, hass, peaqev_discovered: bool = False
    ):
        self.peaq_enabled = HubMember(
            initval=options.misc_options.enabled_on_boot, data_type=bool
        )
        self.hvac_tolerance = options.hvac_tolerance
        self.average_temp_indoors = Average(entities=options.indoor_tempsensors)
        self.average_temp_outdoors = Average(
            entities=options.outdoor_tempsensors,
            observer_message="temperature outdoors changed",
            hub=hub,
        )
        self.temp_trend_indoors = Gradient(max_samples=20, max_age=7200, precision=1)
        self.temp_trend_outdoors = Gradient(max_samples=20, max_age=7200, precision=1)
        self.set_temp_indoors = TargetTemp(
            observer_message="set temperature changed", hub=hub
        )

        if peaqev_discovered:
            self.peaqev_installed = True
            self.peaqev_facade = PeaqevFacade(hass)
        else:
            self.peaqev_installed = False

    def get_tempdiff(self) -> float:
        _indoors = getattr(self.average_temp_indoors, "value", 0)
        _set_temp = getattr(self.set_temp_indoors, "adjusted_temp", 0)
        return _indoors - _set_temp

    def get_tempdiff_in_out(self) -> float:
        _indoors = getattr(self.average_temp_indoors, "value", 0)
        _outdoors = getattr(self.average_temp_outdoors, "value", 0)
        return _indoors - _outdoors