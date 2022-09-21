import logging
import time

_LOGGER = logging.getLogger(__name__)

UPDATE_TIMER = 30

import time

class Gradient:
    _t: list = []
    _gradient: float = 0
    _max_age = 7200
    _max_samples = 20

    @property
    def gradient(self):
        return round(self._gradient,3)

    def set_gradient(self):
        self.remove_from_list()
        temps = self._t
        samples = len(temps)-1
        if samples > 0:
            x1 = temps[0][0]
            x2 = temps[samples][0]
            y1 = temps[0][1]
            y2 = temps[samples][1]
            x = (y2 - y1) / ((x2 - x1)/3600)
            self._gradient = x

    def add_to_list(self, val:float, t:time = time.time()):
        self._t.append((t, val))
        self.remove_from_list()
        self.set_gradient()

    def remove_from_list(self):
        while len(self._t) > self._max_samples:
            self._t.pop(0)
        gen = (x for x in self._t if time.time() - int(x[0]) > self._max_age)
        for i in gen:
            self._t.remove(i)

#g = Gradient()
#g.add_to_list(22.5,1663754400)
#g.add_to_list(21.5, 1663758000)
#g.add_to_list(23.5, 1663765740)
#print(g.gradient)

#https://www.epochconverter.com/

class Trend:
    def __init__(self, hass, entity:str):
        self._value: float = 0
        self._update_timer = 0
        self._hass = hass
        self._entity: str = entity

    @property
    def entity(self) -> str:
        return self._entity

    @property
    def value(self) -> float:
        if time.time() - self._update_timer > UPDATE_TIMER:
            self.value = 1
        return self._value

    @value.setter
    def value(self, val) -> None:
        self._update_timer = time.time()
        ret = self._hass.states.get(self.entity)
        if ret is not None:
            try:
                ret_attr = ret.attributes.get("gradient")
                if isinstance(ret_attr, float):
                    ret = round(ret_attr * (60 ^ 2), 2)
                    self._value = ret
                else:
                    return
            except Exception as e:
                _LOGGER.debug(f"Could not update trend with value {val}")

