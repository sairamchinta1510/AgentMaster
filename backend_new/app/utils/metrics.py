import time
from functools import wraps
from typing import Callable


def count_tokens(text: str) -> int:
    """
    Estimate token count for a text string.
    Rough approximation: 1 token ~= 4 characters for English text.
    """
    return len(text) // 4


class Timer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time = None
        self.elapsed_ms = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = int((time.time() - self.start_time) * 1000)


def timed(func: Callable) -> Callable:
    """Decorator to log execution time of a function."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        with Timer() as timer:
            result = func(*args, **kwargs)
        print(f"{func.__name__} took {timer.elapsed_ms}ms")
        return result
    return wrapper
