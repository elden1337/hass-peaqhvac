import time

class WaitTimer:
    def __init__(self, timeout: int):
        self._timeout = timeout
        self._base_timeout = timeout
        self._last_update = 0

    def update(self, override=None) -> None:
        if override is not None:
            self._timeout = override
        else:
            self._last_update = time.time()

    def reset(self) -> None:
        self._last_update = 0
        self._timeout = self._base_timeout

    def is_timeout(self) -> bool:
        if time.time() - self._last_update > self._timeout:
            self._last_update = time.time()
            self._timeout = self._base_timeout
            return True
        return False