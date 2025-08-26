import asyncio
from functools import wraps

interrupt_event = asyncio.Event()


def coro(f):
    """Auxiliary decorator to make click commands async be default"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(f(*args, **kwargs))
        except KeyboardInterrupt:
            interrupt_event.set()
            loop.run_until_complete(loop.shutdown_asyncgens())

    return wrapper
