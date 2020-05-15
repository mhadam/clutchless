from typing import Sequence, Mapping

from colorama import Fore, init, deinit

from clutchless.subcommand.link import LinkResult


def print_incompletes(incompletes: Sequence[Mapping]):
    if len(incompletes) > 0:
        for item in incompletes:
            print(f'{item["name"]}')


def print_linked(result: LinkResult):
    init()
    if result.no_incompletes:
        print(
            Fore.GREEN
            + f"\N{check mark} No torrents in Transmission with missing data to link."
        )
    else:
        for failure in result.failures:
            if failure.matched:
                print(
                    Fore.RED
                    + f"\N{ballot x} couldn't link {failure.name} because: {failure.result}"
                )
            else:
                print(
                    Fore.RED
                    + f"\N{ballot x} couldn't find matching data to link {failure.name}"
                )
        for success in result.successes:
            print(
                Fore.GREEN
                + f"\N{check mark} linked {success.name} at {success.location.resolve(strict=True)}"
            )
    deinit()
