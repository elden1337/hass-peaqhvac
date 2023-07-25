import time

class WaitTimer:
    def __init__(self, timeout: int):
        self._timeout = timeout
        self._last_update = 0

    def update(self) -> None:
        self._last_update = time.time()

    def reset(self) -> None:
        self._last_update = 0

    def is_timeout(self) -> bool:
        if time.time() - self._last_update > self._timeout:
            self._last_update = time.time()
            return True
        return False