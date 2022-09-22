import logging
import time

_LOGGER = logging.getLogger(__name__)

UPDATE_TIMER = 120

from datetime import datetime
import time

class Gradient:
    def __init__(self, max_age:int, max_samples:int):
        self._temp_readings = []
        self._gradient = 0
        self._max_age = max_age
        self._max_samples = max_samples
        self._latest_update = 0

    @property
    def gradient(self) -> float:
        if time.time() - self._latest_update > UPDATE_TIMER and len(self._temp_readings) > 0:
            self.add_reading(val=self._temp_readings[0][1], t=time.time())
        return round(self._gradient,2)

    @property
    def samples(self) -> int:
        return len(self._temp_readings)

    @property
    def oldest_sample(self) -> str:
        if len(self._temp_readings) > 0:
            return self._dt_from_epoch(self._temp_readings[0][0])
        return datetime.min

    @property
    def newest_sample(self) -> str:
        if len(self._temp_readings) > 0:
            return self._dt_from_epoch(self._temp_readings[-1][0])
        return datetime.min

    def _dt_from_epoch(self, epoch:int) -> str:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(epoch))

    def set_gradient(self):
        self._remove_from_list()
        temps = self._temp_readings
        samples = len(temps)-1
        if samples > 0:
            x1 = temps[0][0]
            x2 = temps[samples][0]
            y1 = temps[0][1]
            y2 = temps[samples][1]
            try:
                x = (y2 - y1) / ((x2 - x1)/3600)
                self._gradient = x
            except ZeroDivisionError as e:
                _LOGGER.warning({e})
                self._gradient = 0

    def add_reading(self, val:float, t:int):
        self._temp_readings.append((t, val))
        self._latest_update = time.time()
        self._remove_from_list()
        self.set_gradient()

    def _remove_from_list(self):
        while len(self._temp_readings) > self._max_samples:
            self._temp_readings.pop(0)
        gen = (x for x in self._temp_readings if time.time() - int(x[0]) > self._max_age)
        for i in gen:
            self._temp_readings.remove(i)
