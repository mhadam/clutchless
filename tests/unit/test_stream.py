import asyncio
from pathlib import Path

import pytest

from clutchless.stream import combine


@pytest.mark.asyncio
async def test_combine_cancel():
    async def _test():
        await asyncio.sleep(1000)
        yield Path()

    gens = {_test()}

    async def _ex():
        async for result in combine(gens):
            pass
        return "finished up"

    task = asyncio.create_task(_ex())
    await asyncio.sleep(0.001)
    task.cancel()
    await task
    assert task.result() == "finished up"
