from datetime import datetime

class EventProperty:
    def __init__(self, name, prop_type: type, hass, default=None):
        self._value = default
        self._hass = hass
        self.name = name
        self._timeout = None
        self._prop_type = prop_type

    @property
    def value(self):
        if self._prop_type == bool:
            if self._value and self._is_timeout():
                self._value = False
        return self._value

    @value.setter
    def value(self, val):
        if self._value != val:
            self._value = val
            self._hass.bus.fire(f"peaqhvac.{self.name}_changed", {"new": val})

    def _is_timeout(self) -> bool:
        if self._timeout is None:
            return False
        return self._timeout < datetime.now()
    @property
    def timeout(self):
        return self._timeout

    @timeout.setter
    def timeout(self, val: datetime|None):
        self._timeout = val