from homeassistant.core import HomeAssistant

from custom_components.peaqhvac.service.hvac.hvactypes.ivt import IVT
from custom_components.peaqhvac.service.hvac.hvactypes.nibe import Nibe
from custom_components.peaqhvac.service.hvac.hvactypes.thermia import Thermia
from custom_components.peaqhvac.service.hvac.interfaces.ihvactype import IHvacType
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.models.enums.hvacbrands import \
    HvacBrand


class HvacFactory:
    HVACTYPES = {HvacBrand.Nibe: Nibe, HvacBrand.IVT: IVT, HvacBrand.Thermia: Thermia}

    @staticmethod
    def create(hass: HomeAssistant, options: ConfigModel, hub, observer) -> IHvacType:
        return HvacFactory.HVACTYPES[options.hvacbrand](hass=hass, hub=hub, observer=observer)
