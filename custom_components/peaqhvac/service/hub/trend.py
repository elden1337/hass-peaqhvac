import logging
import time

_LOGGER = logging.getLogger(__name__)

UPDATE_TIMER = 30

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

