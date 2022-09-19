import logging

_LOGGER = logging.getLogger(__name__)

class Average:
    def __init__(self, entities:list[str]):
        self.listenerentities = entities
        self._value: float = 0
        self._values = {}

        for i in self.listenerentities:
            self._values[i] = 0.0

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, val):
        try:
            filteredlist = [i for i in val.values() if i != 0.0]
            ret = sum(filteredlist) / len(filteredlist)
            self._value = ret
            #_LOGGER.debug(f"values are: {val}")
        except:
            self._value = 0
            _LOGGER.debug("unable to set averagesensor")

    def update_values(self, entity, value):
        try:
            floatval = (float(value))
            if isinstance(floatval, float):
                self._values[entity] = floatval
                self.value = self._values
        except:
            _LOGGER.debug(f"unable to set average-val for {entity}: {value}")
            return
