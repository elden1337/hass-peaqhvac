from dataclasses import dataclass

from peaqevcore.common.models.observer_types import ObserverTypes


@dataclass
class Command:
    command: ObserverTypes
    expiration: float = None
    argument: any = None

    def __eq__(self, other):
        if all([self.command == other.command, self.argument == other.argument]):
            return True
        return False

    def __hash__(self):
        # Create a hash using the attributes of the command
        return hash((self.command, self.expiration, self.argument))

