from abc import abstractmethod
import logging
import time
from datetime import datetime
from typing import Tuple

import custom_components.peaqhvac.extensionmethods as ex
from custom_components.peaqhvac.service.hvac.house_heater import HouseHeater
from custom_components.peaqhvac.service.hvac.offset import Offset
from homeassistant.core import (
    HomeAssistant
)
from custom_components.peaqhvac.service.hvac.water_heater import WaterHeater
from custom_components.peaqhvac.service.models.hvacmode import HvacMode
from custom_components.peaqhvac.service.models.hvacoperations import HvacOperations
from custom_components.peaqhvac.service.models.sensortypes import SensorType

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVALS = {
    HvacOperations.Offset:     900,
    HvacOperations.WaterBoost: 600,
    HvacOperations.VentBoost:  1800
}


class IHvac:
    current_offset: int = 0
    current_offset_dict: dict = {}
    current_offset_dict_tomorrow: dict = {}
    periodic_update_list: list = []
    listenerentities = []

    def __init__(self, hass: HomeAssistant, hub):
        self.hub = hub
        self._hass = hass
        self.house_heater = HouseHeater(hvac=self)
        self.water_heater = WaterHeater(hvac=self)
        self.periodic_update_timers: dict = {
            HvacOperations.Offset:     0,
            HvacOperations.WaterBoost: 0,
            HvacOperations.VentBoost:  0
        }

    @property
    def update_offset(self) -> bool:
        try:
            ret = self.hub.offset.getoffset(
            prices=self.hub.nordpool.prices,
            prices_tomorrow=self.hub.nordpool.prices_tomorrow
            )
            self.current_offset_dict = ret[0]
            self.current_offset_dict_tomorrow = ret[1]
            _hvac_offset = self.hvac_offset
            new_offset = self.house_heater.get_current_offset(ret[0])
            if new_offset != self.current_offset:
                self.current_offset = new_offset
            if self.current_offset != _hvac_offset:
                return True
            return False
        except Exception as e:
            _LOGGER.exception(f"Error on updating offsets: {e}")
            return False

    @property
    @abstractmethod
    def delta_return_temp(self):
        pass

    @property
    @abstractmethod
    def hvac_mode(self) -> HvacMode:
        pass

    @property
    def hvac_offset(self) -> int:
        return self.get_value(SensorType.Offset, int)

    @property
    def hvac_dm(self) -> int:
        return self.get_value(SensorType.DegreeMinutes, int)

    @property
    def hvac_electrical_addon(self) -> float:
        return self.get_value(SensorType.ElectricalAddition, float)

    @property
    def hvac_compressor_start(self) -> int:
        return self.get_value(SensorType.DMCompressorStart, int)

    @property
    def hvac_watertemp(self) -> float:
        val = self.get_value(SensorType.WaterTemp, float)
        self.water_heater.current_temperature = val
        return val

    async def update_hvac(self) -> None:
        self.house_heater.update_demand()
        self.water_heater.update_demand()
        await self.request_periodic_updates()

    async def request_periodic_updates(self) -> None:
        if self.house_heater.vent_boost:
            if time.time() - self.periodic_update_timers[HvacOperations.VentBoost] > UPDATE_INTERVALS[HvacOperations.VentBoost]:
                self.periodic_update_list.append((HvacOperations.VentBoost, 1))
        if self.water_heater.heat_water or self.water_heater.water_heating:
            if time.time() - self.periodic_update_timers[HvacOperations.WaterBoost] > UPDATE_INTERVALS[HvacOperations.WaterBoost]:
                _LOGGER.debug(f"MOCK: Wanting to update hotwaterboost with value {int(self.water_heater.heat_water)}")
                #self.periodic_update_list.append((HvacOperations.WaterBoost, int(self.water_heater.heat_water)))
        if self.update_offset:
            if time.time() - self.periodic_update_timers[HvacOperations.Offset] > UPDATE_INTERVALS[HvacOperations.Offset] or datetime.now().minute == 0:
                self.periodic_update_list.append((HvacOperations.Offset, self.current_offset))
        return await self._do_periodic_updates()

    async def _do_periodic_updates(self) -> None:
        if len(self.periodic_update_list) > 0:
            for u in self.periodic_update_list:
                await self.update_system(operation=u[0], set_val=u[1])
                self.periodic_update_timers[u[0]] = time.time()
            self.periodic_update_list = []

    def _handle_sensor(self, sensor: str):
        sensorobj = sensor.split('|')
        if 0 < len(sensorobj) <= 2:
            ret = self._hass.states.get(sensorobj[0])
            if ret is not None:
                if len(sensorobj) == 2:
                    try:
                        ret_attr = ret.attributes.get(sensorobj[1])
                        return ret_attr
                    except Exception as e:
                        _LOGGER.exception(e)
                else:
                    return ret.state
            return None
        raise ValueError

    def _get_sensors_for_callback(self, types: dict) -> list:
        ret = []
        for t in types:
            item = types[t]
            ret.append(item.split('|')[0])
        self.listenerentities = ret
        return ret

    async def update_system(self, operation: HvacOperations, set_val: any = None):
        if self.hub.sensors.peaq_enabled.value is True:
            _value = 0
            if self.hub.sensors.average_temp_outdoors.initialized_percentage > 0.5:
                _value = await self._get_operation_value(operation, set_val)
                call_operation, params, domain = await self._get_operation_call_parameters(operation, _value)

                _LOGGER.debug(f"Requesting to update hvac-{operation.name} with value {set_val}")
                await self._hass.services.async_call(
                    domain,
                    call_operation,
                    params
                )

    def get_value(self, sensor: SensorType, returntype):
        _sensor = self.get_sensor(sensor)
        ret = self._handle_sensor(_sensor)
        if ret is not None:
            try:
                return ex.parse_to_type(ret, returntype)
            except Exception as e:
                _LOGGER.debug(f"Could not parse {sensor.name} from hvac. {e}")
        else:
            _LOGGER.warning(f"Could not get {sensor.name} from hvac.")
        return 0

    @abstractmethod
    def get_sensor(self, sensor: SensorType = None):
        pass

    @abstractmethod
    async def _get_operation_call_parameters(self, operation: HvacOperations, _value: any) -> Tuple[str, dict, str]:
        pass

    @abstractmethod
    async def _get_operation_value(self, operation: HvacOperations, set_val: any = None):
        pass
