from custom_components.peaqhvac.service.models.demand import Demand
import logging

_LOGGER = logging.getLogger(__name__)


class IHeater:
    def __init__(self, hvac):
        self._demand = Demand.NoDemand
        self._hvac = hvac
        self._control_module = False

    @property
    def demand(self) -> Demand:
        if self._demand is not None:
            return self._demand
        _LOGGER.error(f"{__name__} had no value for Demand.")
        return Demand.NoDemand

    @property
    def control_module(self) -> bool:
        return self._control_module

    @control_module.setter
    def control_module(self, val) -> None:
        self._control_module = val

    def _get_demand_for_current_hour(self) -> Demand:
        # if vacation or similar, return NoDemand
        pass

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not

