from datetime import datetime
from .models.demand import Demand

class WaterDemandObj:
    days: dict[int, dict[int, Demand]]


class WaterHeater:
    def __init__(self):
        pass

    def _get_demand_for_current_hour(self) -> Demand:
        # if vacation or similar, return NoDemand
        pass

    def _get_demand_temperature(self, input: Demand) -> int:
        DEMANDLIMITS = {
            Demand.HighDemand: 40,
            Demand.MediumDemand: 30,
            Demand.LowDemand: 25,
            Demand.NoDemand: 15
        }
        return DEMANDLIMITS[input]

    # def compare to heating demand
    # def get current water temp from nibe
    # def turn on waterboost or not

