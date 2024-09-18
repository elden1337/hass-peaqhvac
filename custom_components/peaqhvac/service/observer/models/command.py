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
        def make_hashable(obj):
            if isinstance(obj, (tuple, list)):
                return tuple(make_hashable(e) for e in obj)
            if isinstance(obj, dict):
                return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
            if isinstance(obj, set):
                return tuple(sorted(make_hashable(e) for e in obj))
            return obj

        return hash((self.command, make_hashable(self.argument)))

