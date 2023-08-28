DOMAIN = "peaqhvac"
PLATFORMS = ["sensor", "binary_sensor", "switch", "climate", "number"]
DOMAIN_DATA = f"{DOMAIN}_data"
LISTENER_FN_CLOSE = "update_listener_close_fn"

PEAQENABLED = "enabled"
TRENDSENSOR_INDOORS = "Temperature trend indoors"
TRENDSENSOR_OUTDOORS = "Temperature trend outdoors"

AVERAGESENSOR_INDOORS = "Average temperature indoors"
AVERAGESENSOR_OUTDOORS = "Average temperature outdoors"
WATERDEMAND = "Water demand"
HEATINGDEMAND = "Heating demand"
CLIMATE_SENSOR = "Climate control"

AVERAGESENSORS = [AVERAGESENSOR_INDOORS, AVERAGESENSOR_OUTDOORS]

TRENDSENSORS = {
    TRENDSENSOR_INDOORS: "mdi:home-thermometer",
    TRENDSENSOR_OUTDOORS: "mdi:sun-thermometer",
}

DEMANDSENSORS = {WATERDEMAND: "mdi:water-boiler", HEATINGDEMAND: "mdi:heat-pump"}

HVACBRAND_NIBE = "Nibe"
HVACBRAND_IVT = "IVT"
HVACBRAND_THERMIA = "Thermia"


LATEST_WATER_BOOST = "latest_water_boost"
NEXT_WATER_START = "next_water_start"