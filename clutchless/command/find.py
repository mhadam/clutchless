import asyncio
import itertools
from pathlib import Path

from colorama import init, deinit, Fore

from clutchless.command.command import Command, CommandResult
from clutchless.spec.find import FindArgs
from clutchless.search import SearchResult
from clutchless.domain.torrent import MetainfoFile


class FindResult(CommandResult):
    def __init__(self, result: SearchResult):
        self.result: SearchResult = result

    @staticmethod
    def print_found(torrent: MetainfoFile, path: Path):
        print(
            Fore.GREEN + f"\N{check mark} {torrent.name} at {path.resolve(strict=True)}"
        )

    @staticmethod
    def print_missing(torrent: MetainfoFile):
        print(Fore.RED + f"\N{ballot x} {torrent.name}")

    def get_torrent(self, hash_string: str) -> MetainfoFile:
        return self.result.file_store.get_torrent(hash_string)

    def output(self):
        init()
        matches_count = len(self.result.found)
        if matches_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Found {matches_count} torrents:")
            for (torrent_hash, path) in self.result.found.items():
                torrent = self.get_torrent(torrent_hash)
                self.print_found(torrent, path)
        misses_count = len(self.result.not_found)
        if misses_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
            for torrent_hash in self.result.not_found:
                torrent = self.get_torrent(torrent_hash)
                self.print_missing(torrent)
        deinit()


async def waiting_animation():
    async def generator():
        for symbol in itertools.cycle("|/-\\"):
            await asyncio.sleep(0.5)
            yield symbol

    async for value in generator():
        print(f"\r{value}", end="")


class FindCommand(Command):
    def __init__(self, find_args: FindArgs):
        self.find_args = find_args

    def run(self) -> FindResult:
        task = asyncio.run(search_task(self.find_args), debug=True)
        return task


async def verifying_search_task(find_args: FindArgs) -> FindResult:
    searcher = find_args.get_async_searcher()
    data_dirs = find_args.get_data_dirs()
    torrent_files = find_args.get_torrent_files()
    loop = asyncio.get_event_loop()
    loop.set_debug(enabled=True)
    task = asyncio.create_task(searcher.get_matches(torrent_files, data_dirs))
    animation_task = asyncio.create_task(waiting_animation())
    search_result: SearchResult = await task
    animation_task.cancel()
    return FindResult(search_result)


async def search_task(find_args: FindArgs):
    searcher = find_args.get_name_matching_searcher()
    data_dirs = find_args.get_data_dirs()
    torrent_files = find_args.get_torrent_files()
    loop = asyncio.get_event_loop()
    loop.set_debug(enabled=True)
    task = asyncio.create_task(searcher.get_matches(torrent_files, data_dirs))
    animation_task = asyncio.create_task(waiting_animation())
    search_result: SearchResult = await task
    animation_task.cancel()
    return FindResult(search_result)
