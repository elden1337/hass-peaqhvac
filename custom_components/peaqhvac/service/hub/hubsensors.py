from typing import Tuple

from peaqevcore.common.models.observer_types import ObserverTypes
from peaqevcore.models.hub.hubmember import HubMember
import logging
from custom_components.peaqhvac.service.hub.average import Average
from custom_components.peaqhvac.service.hub.target_temp import TargetTemp
from peaqevcore.common.trend import Gradient
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.peaqev_facade import (
    PeaqevFacade,
    PeaqevFacadeBase,
)

_LOGGER = logging.getLogger(__name__)


class HubSensors:
    peaqhvac_enabled: HubMember
    temp_trend_outdoors: Gradient
    temp_trend_indoors: Gradient
    dm_trend: Gradient
    set_temp_indoors: TargetTemp
    average_temp_indoors: Average
    average_temp_outdoors: Average
    hvac_tolerance: int
    peaqev_installed: bool
    peaqev_facade: PeaqevFacadeBase

    def __init__(self, observer, options: ConfigModel, hass):
        self.peaqhvac_enabled = HubMember(
            initval=options.misc_options.enabled_on_boot, data_type=bool
        )
        self.hvac_tolerance = options.hvac_tolerance
        self.average_temp_indoors = Average(entities=options.indoor_tempsensors)
        self.average_temp_outdoors = Average(
            entities=options.outdoor_tempsensors,
            observer_message=ObserverTypes.TemperatureOutdoorsChanged,
            observer=observer,
        )
        self.temp_trend_indoors = Gradient(
            max_samples=100, max_age=7200, precision=1, outlier=1, ignore=0
        )
        self.temp_trend_outdoors = Gradient(
            max_samples=100, max_age=7200, precision=1, outlier=1
        )
        self.dm_trend = Gradient(max_age=3600, max_samples=100, precision=0)
        self.set_temp_indoors = TargetTemp(
            observer_message=ObserverTypes.SetTemperatureChanged,
            average_temp_outdoors=self.average_temp_outdoors,
            observer=observer,
        )

        if options.misc_options.peaqev_discovered:
            self.peaqev_installed = True
            self.peaqev_facade = PeaqevFacade(hass, True)
        else:
            self.peaqev_facade = PeaqevFacadeBase()
            self.peaqev_installed = False

    @property
    def predicted_temp(self) -> float:
        return self.average_temp_indoors.value + self.temp_trend_indoors.trend

    @property
    def tolerances(self) -> Tuple[float, float]:
        return self.set_temp_indoors.min_tolerance, self.set_temp_indoors.max_tolerance

    def get_tempdiff(self) -> float:
        _indoors = getattr(self.average_temp_indoors, "value", 0)
        _set_temp = getattr(self.set_temp_indoors, "adjusted_temp", 0)
        if _indoors == 0 and _set_temp != 0:
            return 0
        return _indoors - _set_temp

    def get_tempdiff_in_out(self) -> float:
        _indoors = getattr(self.average_temp_indoors, "value", 0)
        _outdoors = getattr(self.average_temp_outdoors, "value", 0)
        return _indoors - _outdoors
