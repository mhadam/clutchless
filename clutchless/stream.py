import asyncio
from typing import Iterable, TypeVar, AsyncGenerator


async def _anext(gen):
    return gen, await gen.__anext__()


T = TypeVar("T")


async def combine(
    gens: Iterable[AsyncGenerator[T, None]], raise_exc: bool = True
) -> AsyncGenerator[T, None]:
    pending = {asyncio.create_task(_anext(gen)) for gen in gens}
    while pending:
        try:
            done, pending = await asyncio.wait(
                pending, return_when=asyncio.FIRST_COMPLETED
            )
            for future in done:
                try:
                    gen, result = future.result()
                    yield result
                    new_task = asyncio.create_task(_anext(gen))
                    pending.add(new_task)
                except StopAsyncIteration:
                    pass
        except asyncio.CancelledError:
            for task in pending:
                task.cancel()
            if raise_exc:
                raise
