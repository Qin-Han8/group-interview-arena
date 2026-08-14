import asyncio
import sys


def create_runtime_event_loop() -> asyncio.AbstractEventLoop:
    """Create the Psycopg-compatible event loop used by the API server."""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop()
    return asyncio.new_event_loop()
