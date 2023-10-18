from dataclasses import dataclass

@dataclass
class CalculatedOffset:
    current_offset: int
    current_tempdiff: float
    current_temp_extremas: float
    current_temp_trend_offset: float

    def sum_values(self) -> float:
        return sum(
            [
                self.current_offset,
                self.current_tempdiff,
                self.current_temp_extremas,
                self.current_temp_trend_offset,
            ]
        )
    #return int(round(ret, 0))