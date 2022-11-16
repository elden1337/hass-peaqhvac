import logging
from homeassistant.core import (
    HomeAssistant
)
from enum import Enum

_LOGGER = logging.getLogger(__name__)

class Entities(Enum):
    Threshold = 0
    Prediction = 1
    TotalEnergyAccumulated = 2

ENTITIES = {
    Entities.Threshold: {
        "entity":"sensor.peaqev_threshold",
        "attributes":["start_threshold","stop_threshold"]
    },
    Entities.Prediction: {
        "entity": "sensor.peaqev_prediction",
        "attributes": []
    },
    Entities.TotalEnergyAccumulated: {
        "entity": "sensor.peaqev_energy_including_car_hourly",
        "attributes": []
    }
}

class PeaqevFacade:
    def __init__(self, hass: HomeAssistant):
        self._hass = hass

    @property
    def exact_threshold(self) -> float:
        data = self._get_state(ENTITIES[Entities.Threshold])
        if data is not None:
            return float(data["state"])
        return 0

    @property
    def above_stop_threshold(self) -> bool:
        data = self._get_state(ENTITIES[Entities.Threshold])
        if data is not None:
            return float(data["state"]) > (float(data["stop_threshold"]) + 5)
        return False

    @property
    def below_start_threshold(self) -> bool:
        data = self._get_state(ENTITIES[Entities.Threshold])
        if data is not None:
            return float(data["state"]) < float(data["start_threshold"])
        return False

    def _get_state(self, entity_input: dict):
        _entity = entity_input["entity"]
        _attr = entity_input["attributes"] if len(entity_input["attributes"]) > 0 else None
        return self._get_state_from_hass(_entity, *_attr)

    def _get_state_from_hass(self, entity: str, *attributes) -> dict:
        _state = self._hass.states.get(entity)
        ret = {
            "state": _state.state
        }
        if _state is not None:
            if attributes is not None:
                try:
                    for a in attributes:
                        ret_attr = _state.attributes.get(a)
                        ret[a] = ret_attr
                except Exception as e:
                    _LOGGER.exception(f"{e}")
        return ret
