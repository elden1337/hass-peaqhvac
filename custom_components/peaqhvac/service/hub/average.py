import logging

_LOGGER = logging.getLogger(__name__)

class Average:
    def __init__(self, entities:list[str]):
        self.listenerentities = entities
        self._value: float = 0
        self._values = {}
        self._initialized_values = 0
        self._total_sensors = len(self.listenerentities)
        self._initialized_sensors = {}
        
        for i in self.listenerentities:
            self._values[i] = 999.0
            self._initialized_sensors[i] = False

    @property
    def initialized_percentage(self) -> float:
        try:
            return self._initialized_values / self._total_sensors
        except:
            return 0.0
        
    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val):
        try:
            filteredlist = [i for i in val.values() if i != 999.0]
            ret = sum(filteredlist) / len(filteredlist)
            if self.initialized_percentage > 0.2:
                self._value = ret
            self._value = 0
        except:
            self._value = 0
            _LOGGER.debug("unable to set averagesensor")

    def update_values(self, entity, value):
        try:
            floatval = (float(value))
            if isinstance(floatval, float):
                self._values[entity] = floatval
                self.value = self._values
                if self._initialized_sensors[entity] == False:
                    self._initialized_sensors[entity] = True
                    self._initialized_values += 1
        except:
            _LOGGER.debug(f"unable to set average-val for {entity}: {value}")
            return
