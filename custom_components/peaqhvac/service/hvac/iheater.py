from custom_components.peaqhvac.service.models.demand import Demand

class IHeater:
    def __init__(self, hvac):
        self._demand = Demand.NoDemand
        self._hvac = hvac

    @property
    def demand(self) -> Demand:
        return self._demand

    def _get_demand_for_current_hour(self) -> Demand:
        # if vacation or similar, return NoDemand
        pass

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not

