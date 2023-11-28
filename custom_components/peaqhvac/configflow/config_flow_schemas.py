import homeassistant.helpers.config_validation as cv
import voluptuous as vol

USER_SCHEMA = vol.Schema(
    {
        vol.Optional("indoor_tempsensors"): cv.string,
        vol.Optional("outdoor_tempsensors"): cv.string,
        vol.Optional("systemid"): cv.string,
    }
)

OPTIONAL_SCHEMA = vol.Schema({
    vol.Optional("outdoor_temp_stop_heating", default=15): cv.positive_int,
    vol.Optional("non_hours_water_boost", default=[7, 11, 12, 15, 16, 17, 23]): cv.multi_select(list(range(0, 24))),
    vol.Optional("demand_hours_water_boost", default=[]): cv.multi_select(list(range(0, 24))),
    vol.Optional("low_degree_minutes", default=-600): cv.positive_int,
    vol.Optional("very_cold_temp", default=-12): cv.positive_int,
})

