import logging
from homeassistant.core import (
    HomeAssistant
)

_LOGGER = logging.getLogger(__name__)

PEAQEVDOMAIN = "peaqev"

class PeaqevFacade:
    def __init__(self, hass: HomeAssistant):
        self._hass = hass
        self._peaqevhub = hass.data[PEAQEVDOMAIN]["hub"]

    def add_callback(self, message, function):
        self._peaqevhub.observer.add(message, function)

    @property
    def offsets(self) -> dict:
        data = self._peaqevhub.hours.offsets
        if data is not None:
            return data
        return {}

    @property
    def exact_threshold(self) -> float:
        data = self._peaqevhub.prediction.predictedpercentageofpeak
        if data is not None:
            return float(data)
        return 0

    @property
    def above_stop_threshold(self) -> bool:
        try:
            stop = self._peaqevhub.threshold.stop
            current = self.exact_threshold
            return current > (stop + 5)
        except:
            return False

    @property
    def below_start_threshold(self) -> bool:
        try:
            start = self._peaqevhub.threshold.start
            current = self.exact_threshold
            return current < (start)
        except:
            return False

    @property
    def average_this_month(self) -> float:
        try:
            return self._peaqevhub.nordpool.average_month
        except:
            return 0
