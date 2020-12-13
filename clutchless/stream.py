import asyncio
from typing import AsyncIterable, Iterable, AsyncIterator, TypeVar


async def anext(gen):
    return gen, await gen.__anext__()


T = TypeVar("T")


async def combine(gens: Iterable[AsyncIterator[T]]) -> AsyncIterable[T]:
    pending = {anext(gen) for gen in gens}
    while pending:
        try:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
        except asyncio.CancelledError:
            return
        for future in done:
            try:
                gen, result = future.result()
                yield result
                pending.add(anext(gen))
            except StopAsyncIteration:
                pass
