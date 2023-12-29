from custom_components.peaqhvac.service.observer.property_observer import PropertyObserver

class ObservableProperty:
    def __init__(self, observer_message: str, expected_type: type) -> None:
        self.observer_message: str = observer_message
        self._type: type = expected_type
        self._value = None
        PropertyObserver.subscribe(self.observer_message, self.handle_callback)

    @property
    def value(self):
        return self._value
    
    def handle_callback(self, *args):
        if len(args) != 1:
            raise Exception("ObservableProperty.handle_callback: invalid number of arguments")
        try:
            value = self._type(args[0])
        except ValueError:
            raise Exception("ObservableProperty.handle_callback: unable to parse value to the correct type")
        self._value = value
