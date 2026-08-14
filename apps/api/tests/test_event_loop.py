import asyncio
import sys

from group_interview_arena_api.core.event_loop import create_runtime_event_loop


def test_runtime_event_loop_is_psycopg_compatible_on_windows() -> None:
    event_loop = create_runtime_event_loop()
    try:
        if sys.platform == "win32":
            assert isinstance(event_loop, asyncio.SelectorEventLoop)
    finally:
        event_loop.close()
