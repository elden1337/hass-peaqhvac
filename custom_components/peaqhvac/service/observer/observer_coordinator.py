from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.helpers.event import async_track_time_interval
from peaqevcore.common.models.observer_types import ObserverTypes
from custom_components.peaqhvac.service.observer.iobserver_coordinator import IObserver
from custom_components.peaqhvac.service.observer.models.command import Command
from custom_components.peaqhvac.extensionmethods import async_iscoroutine

_LOGGER = logging.getLogger(__name__)


class Observer(IObserver):
    def __init__(self, hub):
        super().__init__()
        self.hub = hub
        async_track_time_interval(
            self.hub.state_machine, self.async_dispatch, timedelta(seconds=1)
        )

    async def async_broadcast_separator(self, func, command: Command):
        if await async_iscoroutine(func):
            await self.async_call_func(func=func, command=command),
        else:
            await self.hub.state_machine.async_add_executor_job(
                self._call_func, func, command
            )