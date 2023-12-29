class PropertyObserver:
    _observers = {}

    @staticmethod
    def subscribe(message: str, callback):
        if message not in PropertyObserver._observers:
            PropertyObserver._observers[message] = []
        PropertyObserver._observers[message].append(callback)

    @staticmethod
    def publish(message: str, *args):
        if message not in PropertyObserver._observers:
            return
        for callback in PropertyObserver._observers[message]:
            callback(*args)