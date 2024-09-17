from __future__ import annotations

import logging
import time
from abc import abstractmethod
import asyncio
from typing import Callable

from peaqevcore.common.models.observer_types import ObserverTypes

from custom_components.peaqhvac.service.observer.const import (
    COMMAND_WAIT, TIMEOUT)
from custom_components.peaqhvac.service.observer.models.command import \
    Command
from custom_components.peaqhvac.service.observer.models.observer_model import \
    ObserverModel

_LOGGER = logging.getLogger(__name__)



class IObserver:
    """
    Observer class handles updates throughout peaq.
    Attach to hub class and subscribe to updates (string matches) in other classes connected to the hub.
    When broadcasting, you may use one argument that the of-course needs to correspond to your receiving function.
    """

    def __init__(self):
        self.model = ObserverModel()
        self._lock = asyncio.Lock()

    def activate(self, init_broadcast: ObserverTypes = None) -> None:
        self.model.active = True
        if init_broadcast is not None:
            self.broadcast(init_broadcast)

    def deactivate(self) -> None:
        self.model.active = False

    def _check_and_convert_enum_type(self, command) -> ObserverTypes|str:
        if isinstance(command, str):
            try:
                command = ObserverTypes(command)
                _LOGGER.debug(f"Observer.add: command {command} was not of type ObserverTypes but was converted.")
            except ValueError:
                pass
                #return ObserverTypes.Test
        return command

    def add(self, command: ObserverTypes|str, func):
        command = self._check_and_convert_enum_type(command)
        if command in self.model.subscribers.keys():
            self.model.subscribers[command].append(func)
        else:
            self.model.subscribers[command] = [func]

    async def async_broadcast(self, command: ObserverTypes|str, argument=None):
        command = self._check_and_convert_enum_type(command)
        self.broadcast(command, argument)

    def broadcast(self, command: ObserverTypes|str, argument=None):
        _LOGGER.debug(f"received broadcast: {command} - {argument}")
        command = self._check_and_convert_enum_type(command)
        _expiration = time.time() + TIMEOUT
        cc = Command(command, _expiration, argument)
        if cc not in self.model.broadcast_queue:
            self.model.broadcast_queue.append(cc)

    async def async_dispatch(self, *args):
        q: Command
        for q in self.model.broadcast_queue:
            if q.command in self.model.subscribers.keys():
                await self.async_dequeue_and_broadcast(q)

    async def async_dequeue_and_broadcast(self, command: Command):
        if await self.async_ok_to_broadcast(command):
            async with self._lock:
                for func in self.model.subscribers.get(command.command, []):
                    _LOGGER.debug(f"broadcasting {command.command} with {command.argument}")
                    await self.async_broadcast_separator(func, command)
                if command in self.model.broadcast_queue:
                    self.model.broadcast_queue.remove(command)

    @abstractmethod
    async def async_broadcast_separator(self, func, command):
        pass

    @staticmethod
    def _call_func(func: Callable, command: Command) -> None:
        if command.argument is not None:
            if isinstance(command.argument, dict):
                try:
                    func(**command.argument)
                except TypeError:
                    func()
            else:
                try:
                    func(command.argument)
                except TypeError:
                    func()
        else:
            func()

    @staticmethod
    async def async_call_func(func: Callable, command: Command) -> None:
        try:
            if command.argument is not None:
                if isinstance(command.argument, dict):
                    try:
                        await func(**command.argument)
                    except TypeError:
                        await func()
                else:
                    try:
                        await func(command.argument)
                    except TypeError:
                        await func()
            else:
                await func()
        except Exception as e:
            _LOGGER.error(f"async_call_func for {func} with command {command}: {e}")

    async def async_ok_to_broadcast(self, command: Command) -> bool:
        if command not in self.model.wait_queue.keys():
            self.model.wait_queue[command] = time.time()
            return True
        if time.time() - self.model.wait_queue.get(command, 0) > COMMAND_WAIT:
            self.model.wait_queue[command] = time.time()
            return True
        _LOGGER.debug(f"Catched command {command} in wait_queue")
        return False
