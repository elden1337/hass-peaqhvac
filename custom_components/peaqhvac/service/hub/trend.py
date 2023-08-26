import logging
import time
from datetime import datetime

import custom_components.peaqhvac.extensionmethods as ex

_LOGGER = logging.getLogger(__name__)


class Gradient:
    def __init__(
        self, max_age: int, max_samples: int, precision: int = 2, ignore: int = None
    ):
        self._init_time = time.time()
        self._temp_readings = []
        self._gradient = 0
        self._max_age = max_age
        self._max_samples = max_samples
        self._latest_update = 0
        self._ignore = ignore
        self._precision = precision

    @property
    def gradient(self) -> float:
        self.set_gradient()
        return round(self._gradient, self._precision)

    @property
    def gradient_raw(self) -> float:
        self.set_gradient()
        return self._gradient

    @property
    def samples(self) -> int:
        return len(self._temp_readings)

    @property
    def samples_raw(self) -> list:
        return self._temp_readings

    @samples_raw.setter
    def samples_raw(self, lst):
        self._temp_readings.extend(lst)
        self.set_gradient()

    @property
    def oldest_sample(self) -> str:
        if len(self._temp_readings) > 0:
            return ex.dt_from_epoch(self._temp_readings[0][0])
        return datetime.min

    @property
    def newest_sample(self) -> str:
        if len(self._temp_readings) > 0:
            return ex.dt_from_epoch(self._temp_readings[-1][0])
        return datetime.min

    @property
    def is_clean(self) -> bool:
        return all([time.time() - self._init_time > 300, self.samples > 1])

    def set_gradient(self):
        self._remove_from_list()
        temps = self._temp_readings
        if len(temps) - 1 > 0:
            try:
                x = (temps[-1][1] - temps[0][1]) / ((time.time() - temps[0][0]) / 3600)
                self._gradient = x
            except ZeroDivisionError as e:
                _LOGGER.warning({e})
                self._gradient = 0

    def add_reading(self, val: float, t: float):
        if self._ignore is None or self._ignore < val:
            self._temp_readings.append((int(t), round(val, 3)))
            self._latest_update = time.time()
            self._remove_from_list()
            self.set_gradient()

    def _remove_from_list(self):
        """Removes overflowing number of samples and old samples from the list."""
        while len(self._temp_readings) > self._max_samples:
            self._temp_readings.pop(0)
        gen = (
            x for x in self._temp_readings if time.time() - int(x[0]) > self._max_age
        )
        for i in gen:
            if len(self._temp_readings) > 2:
                # Always keep two readings to be able to calc trend
                self._temp_readings.remove(i)

    async def async_set_gradient(self):
        await self.async_remove_from_list()
        temps = self._temp_readings
        if len(temps) - 1 > 0:
            try:
                x = (temps[-1][1] - temps[0][1]) / ((time.time() - temps[0][0]) / 3600)
                self._gradient = x
            except ZeroDivisionError as e:
                _LOGGER.warning({e})
                self._gradient = 0

    async def async_add_reading(self, val: float, t: float):
        if self._ignore is None or self._ignore < val:
            self._temp_readings.append((int(t), round(val, 3)))
            self._latest_update = time.time()
            self._remove_from_list()
            await self.async_set_gradient()

    async def async_remove_from_list(self):
        """Removes overflowing number of samples and old samples from the list."""
        while len(self._temp_readings) > self._max_samples:
            self._temp_readings.pop(0)
        gen = (
            x for x in self._temp_readings if time.time() - int(x[0]) > self._max_age
        )
        for i in gen:
            if len(self._temp_readings) > 2:
                # Always keep two readings to be able to calc trend
                self._temp_readings.remove(i)
