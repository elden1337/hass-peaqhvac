from peaqevcore.common.models.observer_types import ObserverTypes


class ObserverBroadcaster:
    def __init__(self, message: ObserverTypes, hub):
        self._observer_message = message
        self.hub = hub

    def _broadcast_changes(self, val=None):
        if self._observer_message is not None:
            self.hub.observer.broadcast(self._observer_message, val)
