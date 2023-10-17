from statistics import mean

class HouseHeaterTemperatureHelper:
    def __init__(self, hub):
        self._hub = hub

    def get_tempdiff_inverted(self, current_offset) -> int:
        diff = self._hub.sensors.get_tempdiff()
        if diff == 0:
            return 0
        _tolerance = self._determine_tolerance(diff, current_offset)
        return int(diff / _tolerance) * -1

    def get_temp_extremas(self, current_offset) -> float:
        set_temp = self._hub.sensors.set_temp_indoors.adjusted_temp
        diffs = [set_temp - t for t in self._hub.sensors.average_temp_indoors.all_values]
        cold_diffs, hot_diffs = [d for d in diffs if d > 0] + [0], [d for d in diffs if d < 0] + [0]
        hot_large = abs(min(hot_diffs))
        cold_large = abs(max(cold_diffs))
        if hot_large == cold_large:
            return 0
        is_cold = cold_large > hot_large
        tolerance = self._determine_tolerance(is_cold, current_offset)
        if is_cold:
            return self.temp_extremas_return(cold_diffs, tolerance)
        return self.temp_extremas_return(hot_diffs, tolerance)

    @staticmethod
    def temp_extremas_return(diffs, tolerance) -> float:
        diffs.pop()
        div = len(diffs)
        ret = (mean(diffs) - tolerance) * div
        return round(ret / div, 2)

    def get_temp_trend_offset(self, current_offset) -> float:
        if not self._hub.sensors.temp_trend_indoors.is_clean:
            return 0

        gradient = self._hub.sensors.temp_trend_indoors.gradient
        if -0.1 < gradient < 0.1:
            return 0

        predicted_temp = self._hub.predicted_temp
        set_temp = self._hub.sensors.set_temp_indoors.adjusted_temp
        new_temp_diff = predicted_temp - set_temp

        tolerance = self._determine_tolerance(new_temp_diff, current_offset)
        if abs(new_temp_diff) < tolerance:
            return 0

        offset_steps = self._get_offset_steps(tolerance)
        if new_temp_diff > 0:
            offset_steps *= -1
        if offset_steps == 0:
            return 0

        return offset_steps

    def _determine_tolerance(self, determinator, current_offset) -> float:
        tolerances = self._hub.sensors.set_temp_indoors.adjusted_tolerances(
            current_offset
        )
        return (
            tolerances[1]
            if (determinator > 0 or determinator is True)
            else tolerances[0]
        )

    def _get_offset_steps(self, tolerance) -> int:
        ret = abs(self._hub.sensors.temp_trend_indoors.gradient) / tolerance
        return int(ret)