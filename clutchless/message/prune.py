from colorama import Fore

from clutchless.subcommand.prune import PrunedResult


def print_pruned(result: PrunedResult, dry_run: bool):
    if dry_run:
        print("These are dry-run results.")
    if len(result.successes) > 0:
        print("Following torrents have been pruned:")
        for success in result.successes:
            print(Fore.GREEN + f"\N{check mark} {success.name}")
    if len(result.failures) > 0:
        print("Following torrents have failed to be pruned:")
        for failure in result.failures:
            print(
                Fore.RED + f"\N{ballot x} {failure.name} failed to be pruned because: {failure.error_string}."
            )
