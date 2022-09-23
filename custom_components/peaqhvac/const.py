DOMAIN = "peaqhvac"
PLATFORMS = ["sensor", "binary_sensor", "switch"]
DOMAIN_DATA = f"{DOMAIN}_data"
LISTENER_FN_CLOSE = "update_listener_close_fn"

PEAQENABLED = "enabled"
TRENDSENSOR_INDOORS = "Temperature trend indoors"
TRENDSENSOR_OUTDOORS = "Temperature trend outdoors"

AVERAGESENSOR_INDOORS = "Average temperature indoors"
AVERAGESENSOR_OUTDOORS = "Average temperature outdoors"
WATERDEMAND = "Water demand"
HEATINGDEMAND = "Heating demand"

DEMANDSENSORS = {
    WATERDEMAND: "mdi:water-boiler",
    HEATINGDEMAND: "mdi:heat-pump"
}

HVACBRAND_NIBE = "Nibe"
HVACBRAND_IVT = "IVT"
HVACBRAND_THERMIA = "Thermia"