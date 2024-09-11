from peaqevcore.common.models.observer_types import ObserverTypes


class ObserverBroadcaster:
    def __init__(self, message: ObserverTypes, observer):
        self._observer_message = message
        self.observer = observer

    def _broadcast_changes(self):
        if self._observer_message is not None:
            self.observer.broadcast(self._observer_message)
