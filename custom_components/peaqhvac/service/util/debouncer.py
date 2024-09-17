import asyncio


class Debouncer:
    def __init__(self, func: callable, debounce_delay: float = 1):
        self._debounce_delay = debounce_delay
        self._func = func
        self.__task = None

    def debounce(self):
        if self.__task:
            self.__task.cancel()

        async def delayed_func():
            await asyncio.sleep(self._debounce_delay)
            if asyncio.iscoroutinefunction(self._func):
                await self._func()
            else:
                self._func()

        self.__task = asyncio.create_task(delayed_func())