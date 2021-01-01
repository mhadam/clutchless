import asyncio
import logging
import signal
from typing import Set, MutableSequence

from colorama import init, deinit, Fore

from clutchless.command.command import Command, CommandOutput
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import TorrentData
from clutchless.service.torrent import FindService


logger = logging.getLogger(__name__)


class FindOutput(CommandOutput):
    def __init__(self, found: Set[TorrentData], missing: Set[MetainfoFile]):
        self.found = found
        self.missing = missing

    @staticmethod
    def print_found(found: TorrentData):
        name = found.metainfo_file.name
        path = found.location
        print(Fore.GREEN + f"\N{check mark} {name} at {path}")

    @staticmethod
    def print_missing(torrent: MetainfoFile):
        print(Fore.RED + f"\N{ballot x} {torrent.name}")

    def display(self):
        init()
        matches_count = len(self.found)
        if matches_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Found {matches_count} torrents:")
            for linked in self.found:
                self.print_found(linked)
        misses_count = len(self.missing)
        if misses_count > 0:
            print(Fore.LIGHTWHITE_EX + f"Did not find {misses_count} torrents:")
            for file in self.missing:
                self.print_missing(file)
        deinit()

    def dry_run_display(self):
        raise NotImplementedError


class FindCommand(Command):
    def __init__(
        self, find_service: FindService, metainfo_files: Set[MetainfoFile],
    ):
        self.find_service = find_service
        self.metainfo_files = metainfo_files

    def run(self) -> FindOutput:
        async def _find_subroutine():
            collected: MutableSequence[TorrentData] = []
            completion_count = len(self.metainfo_files)
            found_count = 0
            generator = self.find_service.find_async(self.metainfo_files)
            print(f"Starting search - press Ctrl+C to cancel")
            while True:
                try:
                    result = await generator.__anext__()
                    collected.append(result)
                    found_count += 1
                    logger.info(f"found {result}")
                    if result.location:
                        print(
                            f"{found_count}/{completion_count} {result.metainfo_file} found at {result.location}"
                        )
                except StopAsyncIteration:
                    logger.info(f"generator exit")
                    break
                except asyncio.CancelledError:
                    logger.info(f"closing generator")
                    await generator.aclose()
            logger.info(f"finished find subroutine collecting {collected}")
            return collected

        async def _main():
            find_task = asyncio.create_task(_find_subroutine())
            loop = asyncio.get_event_loop()

            def _interrupt():
                find_task.cancel()

            loop.add_signal_handler(signal.SIGINT, _interrupt)
            return await find_task

        results = asyncio.run(_main())
        found = {result for result in results if result.location is not None}
        rest = {result.metainfo_file for result in results if result.location is None}
        logger.info(f"finished with results {found, rest}")
        output = FindOutput(found, rest)
        return output

    def dry_run(self) -> CommandOutput:
        raise NotImplementedError
