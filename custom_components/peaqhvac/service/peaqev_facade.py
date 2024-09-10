import logging

from homeassistant.core import HomeAssistant
from peaqevcore.common.spotprice.spotpricebase import SpotPriceBase
from peaqevcore.services.hourselection.initializers.hoursbase import Hours

_LOGGER = logging.getLogger(__name__)

PEAQEVDOMAIN = "peaqev"

class PeaqevFacadeBase:
    @property
    def offsets(self) -> dict:
        return {}

    @property
    def min_price(self) -> float:
        return 0

    @property
    def exact_threshold(self) -> float:
        return 0

    @property
    def above_stop_threshold(self) -> bool:
        return False

    @property
    def below_start_threshold(self) -> bool:
        return True

    @property
    def average_this_month(self) -> float:
        return 0

    @property
    def spotprice(self) -> SpotPriceBase |None:
        return None

class PeaqevFacade(PeaqevFacadeBase):
    def __init__(self, hass: HomeAssistant, peaqev_discovered: bool):
        self._hass = hass
        if peaqev_discovered:
            self._peaqevhub = hass.data[PEAQEVDOMAIN]["hub"]

    @property
    def peaqev_observer(self):
        return self._peaqevhub.observer

    @property
    def hours(self) -> Hours |None:
        return self._peaqevhub.hours

    @property
    def offsets(self) -> dict:
        data = self._peaqevhub.hours.offsets
        if data is not None:
            return data
        _LOGGER.debug(f"peaqev offsets was None. {self._peaqevhub.hours} ")
        return {}

    @property
    def min_price(self) -> float:
        data = self._peaqevhub.options.price.min_price
        if data is not None:
            return data
        return 0

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
        except Exception as e:
            _LOGGER.exception(f"Error on above_stop_threshold {e}")
            return False

    @property
    def below_start_threshold(self) -> bool:
        try:
            start = self._peaqevhub.threshold.start
            current = self.exact_threshold
            return current < (start)
        except Exception as e:
            _LOGGER.exception(f"Error on below_start_threshold {e}")
            return False

    @property
    def average_this_month(self) -> float:
        try:
            return self._peaqevhub.spotprice.average_month
        except Exception as e:
            _LOGGER.exception(f"Error on average_this_month {e}")
            return 0
