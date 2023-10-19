from statistics import mean

class HouseHeaterTemperatureHelper:
    def __init__(self, hub):
        self._hub = hub

    # def get_tempdiff_inverted(self, current_offset) -> int:
    #     diff = self._hub.sensors.get_tempdiff()
    #     if diff == 0:
    #         return 0
    #     _tolerance = self._determine_tolerance(diff, current_offset)
    #     return int(diff / _tolerance) * -1

    def get_tempdiff_inverted(self, current_offset) -> int:
        diff = self._hub.sensors.get_tempdiff()+ 0.00001
        if abs(diff) < 0.5:
            return 0
        """get the inverted tolerance in this case"""
        _tolerance = self._determine_tolerance(diff * -1, current_offset)
        return int(round((diff / (_tolerance * 4)) * -1, 0))

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
        avg_diff = mean(diffs[:-1])
        dev = 1 if avg_diff >= 0 else -1
        ret = (abs(avg_diff) - tolerance) * dev
        ret = max(ret, 0) if dev == 1 else min(ret, 0)
        return round(ret, 2)

    def get_temp_trend_offset(self) -> float:
        if not self._hub.sensors.temp_trend_indoors.is_clean:
            return 0
        predicted_temp = self._hub.predicted_temp
        set_temp = self._hub.sensors.set_temp_indoors.adjusted_temp
        new_temp_diff = (predicted_temp - set_temp) / 2
        if predicted_temp >= set_temp:
            ret = max(round(new_temp_diff, 1), 0)
        else:
            ret = min(round(new_temp_diff, 1), 0)
        return ret * -1

    def _determine_tolerance(self, determinator, current_offset) -> float:
        tolerances = self._hub.sensors.set_temp_indoors.adjusted_tolerances(
            current_offset
        )
        return (
            tolerances[0]
            if (determinator > 0 or determinator is True)
            else tolerances[1]
        )

    def _get_offset_steps(self, tolerance) -> int:
        ret = abs(self._hub.sensors.temp_trend_indoors.gradient) / tolerance
        return int(ret)