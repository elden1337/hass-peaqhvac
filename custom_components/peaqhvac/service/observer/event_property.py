class EventProperty:
    def __init__(self, name, prop_type: type, hass, default=None):
        self._value = default
        self._hass = hass
        self.name = name
        self._prop_type = prop_type

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        if self._value != val:
            self._value = val
            self._hass.bus.fire(f"peaqhvac.{self.name}_changed", {"new": val})