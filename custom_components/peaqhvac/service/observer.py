from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Tuple

_LOGGER = logging.getLogger(__name__)
COMMAND_WAIT = 3
TIMEOUT = 60


class ObserverBroadcaster:
    def __init__(self, message: str, hub):
        self._observer_message = message
        self.hub = hub

    def _broadcast_changes(self):
        if self._observer_message is not None:
            self.hub.observer.broadcast(self._observer_message)


@dataclass
class ObserverModel:
    subscribers: dict = field(default_factory=lambda: {})
    broadcast_queue: list = field(default_factory=lambda: [])
    wait_queue: dict = field(default_factory=lambda: {})
    active: bool = False


class Observer:
    """
    Observer class handles updates throughout peaqev.
    Attach to hub class and subscribe to updates (string matches) in other classes connected to the hub.
    When broadcasting, you may use one argument that the of-course needs to correspond to your receiving function.
    """

    def __init__(self, hub):
        self.model = ObserverModel()
        self.hub = hub

    def activate(self) -> None:
        self.model.active = True

    def add(self, command: str, func):
        if command in self.model.subscribers.keys():
            self.model.subscribers[command].append(func)
        else:
            self.model.subscribers[command] = [func]

    def broadcast(self, command: str, argument=None):
        _expiration = time.time() + TIMEOUT
        if (command, _expiration) not in self.model.broadcast_queue:
            self.model.broadcast_queue.append((command, _expiration, argument))
        for q in self.model.broadcast_queue:
            if q[0] in self.model.subscribers.keys():
                self._dequeue_and_broadcast(q)

    async def async_broadcast(self, command: str, argument=None):
        await self.hub.state_machine.async_add_executor_job(self.broadcast, command, argument)

    def _prepare_dequeue(self, attempt: int = 0) -> None:
        if self.model.active:
            for q in self.model.broadcast_queue:
                if q[0] in self.model.subscribers.keys():
                    self._dequeue_and_broadcast(q)
        elif attempt < 5:
            _ = self.hub.is_initialized
            attempt += 1
            return self._prepare_dequeue(attempt)

    def _dequeue_and_broadcast(self, command: Tuple[str, int, any]):
        _LOGGER.debug(f"ready to broadcast: {command[0]} with params: {command[2]}")
        if self._ok_to_broadcast(command[0]):
            if command[1] > time.time():
                for func in self.model.subscribers[command[0]]:
                    self._call_func(func, command)
            self.model.broadcast_queue.remove(command)

    @staticmethod
    def _call_func(func, command: Tuple[str, int, any]):
        if command[2] is not None:
            if isinstance(command[2], dict):
                try:
                    func(**command[2])
                except TypeError:
                    func()
            else:
                try:
                    func(command[2])
                except TypeError:
                    func()
        else:
            func()

    # @staticmethod
    # async def async_call_func(func, command: Command):
    #     if command.argument is not None:
    #         if isinstance(command.argument, dict):
    #             try:
    #                 await func(**command.argument)
    #             except TypeError:
    #                 await func()
    #         else:
    #             try:
    #                 await func(command.argument)
    #             except TypeError:
    #                 await func()
    #     else:
    #         await func()

    def _ok_to_broadcast(self, command) -> bool:
        if command not in self.model.wait_queue.keys():
            self.model.wait_queue[command] = time.time()
            return True
        if time.time() - self.model.wait_queue[command] > COMMAND_WAIT:
            self.model.wait_queue[command] = time.time()
            return True
        return False
