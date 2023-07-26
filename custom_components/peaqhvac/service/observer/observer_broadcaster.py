
class ObserverBroadcaster:
    def __init__(self, message: str, hub):
        self._observer_message = message
        self.hub = hub

    def _broadcast_changes(self):
        if self._observer_message is not None:
            self.hub.observer.broadcast(self._observer_message)
