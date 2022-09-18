from abc import abstractmethod
from custom_components.peaqhvac.service.models.hvacbrands import HvacBrand
from custom_components.peaqhvac.service.models.config_model import ConfigModel
from custom_components.peaqhvac.service.models.demand import Demand
from homeassistant.core import (
    HomeAssistant
)


class IHvac:
    waterdemand: Demand = Demand.NoDemand
    hvacdemand: Demand = Demand.NoDemand

    def __init__(self, hass: HomeAssistant, options: ConfigModel):
        pass

    @abstractmethod
    def update_system(self):
        pass


class Nibe(IHvac):
    def update_system(self):
        pass

class IVT(IHvac):
    def update_system(self):
        pass

class Thermia(IHvac):
    def update_system(self):
        pass


class HvacFactory:
    HVACTYPES = {
        HvacBrand.Nibe: Nibe,
        HvacBrand.IVT: IVT,
        HvacBrand.Thermia: Thermia
    }

    @staticmethod
    def create(hass: HomeAssistant, options: ConfigModel) -> IHvac:
        return HvacFactory.HVACTYPES[options.hvacbrand](hass, options)

