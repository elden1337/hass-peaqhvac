import logging
import homeassistant.helpers.template as template

_LOGGER = logging.getLogger(__name__)

NORDPOOL = "nordpool"

class NordPoolUpdater:
    def __init__(self, hass, hub):
        self._hass = hass
        self._hub = hub
        self.currency: str = ""
        self._prices: list = []
        self._prices_tomorrow: list = []
        self._state: float = None
        self.nordpool_entity: str = ""
        self._setup_nordpool()

    @property
    def is_initialized(self) -> bool:
        return all([
            self.currency != "",
            len(self._prices) > 0,
            self._state is not None
        ])

    @property
    def state(self) -> float:
        return self._state

    @state.setter
    def state(self, val) -> None:
        if val != self._state:
            self._state = val

    @property
    def prices(self) -> list:
        # if len(self._prices) > 25:
        #     raise Exception
        return self._prices

    @prices.setter
    def prices(self, val) -> None:
        if val != self._prices:
            self._prices = val
            if not 20 < len(self._prices) < 25:
                _LOGGER.error(f"pricelength is now: {len(self._prices)}")

    @property
    def prices_tomorrow(self) -> list:
        return self._prices_tomorrow

    @prices_tomorrow.setter
    def prices_tomorrow(self, val) -> None:
        if val != self._prices_tomorrow:
            self._prices_tomorrow = val

    async def update_nordpool(self):
        ret = self._hass.states.get(self.nordpool_entity)
        _result = {}
        if ret is not None:
            try:
                _result["today"] = list(ret.attributes.get("today"))
            except Exception as e:
                _LOGGER.exception(f"Could not parse today's prices from Nordpool. Unsolveable error. {e}")
                return
            try:
                _result["tomorrow"] = list(ret.attributes.get("tomorrow"))
            except Exception as e:
                _LOGGER.warning(f"Couldn't parse tomorrow's prices from Nordpool. Array will be empty. {e}")
                _result["tomorrow"] = []
            _result["currency"] = str(ret.attributes.get("currency"))
            _result["state"] = ret.state
            if self._update_set_prices(_result):
                self._hub.observer.broadcast("prices changed", [self._prices, self._prices_tomorrow])
        else:
            _LOGGER.error("Could not get nordpool-prices")

    def _update_set_prices(self, result: dict) -> bool:
        ret = False
        if self.prices != list(result.get("today")):
            self.prices = list(result.get("today"))
            ret = True
        if self.prices_tomorrow != list(result.get("tomorrow")):
            self.prices_tomorrow = list(result.get("tomorrow"))
            ret = True
        self.currency = result.get("currency")
        self.state = result.get("state")
        return ret

    def _setup_nordpool(self):
        try:
            entities = template.integration_entities(self._hass, NORDPOOL)
            if len(list(entities)) < 1:
                raise Exception("no entities found for Nordpool.")
            if len(list(entities)) == 1:
                self.nordpool_entity = list(entities)[0]
                _LOGGER.debug(f"Nordpool has been set up and is ready to be used with {self.nordpool_entity}")
                self.update_nordpool()
            else:
                raise Exception("more than one Nordpool entity found. Cannot continue.")
        except Exception as e:
            msg = f"Peaqhvac was unable to get a Nordpool-entity. Disabling Priceawareness: {e}"
            _LOGGER.error(msg)
