from dataclasses import dataclass, field
from custom_components.peaqhvac.service.observer.models.command import Command

@dataclass
class ObserverModel:
    subscribers: dict = field(default_factory=lambda: {})
    broadcast_queue: list[Command] = field(default_factory=lambda: [])
    wait_queue: dict[Command, float] = field(default_factory=lambda: {})
    dispatch_delay_queue: dict[Command,float] = field(default_factory=lambda: {})
    active: bool = False
