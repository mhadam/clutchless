from dataclasses import dataclass, field
from typing import Set, Mapping

from clutchless.command.command import CommandOutput, Command
from clutchless.service.torrent import PruneService


@dataclass
class PruneClientResult(CommandOutput):
    pruned_names: Set[str] = field(default_factory=set)

    def display(self):
        if len(self.pruned_names) > 0:
            print("The following torrents were pruned:")
            for name in self.pruned_names:
                print(f"{name}")
        else:
            print("No torrents were pruned from client.")

    def dry_run_display(self):
        if len(self.pruned_names) > 0:
            print("The following torrents would be pruned:")
            for name in self.pruned_names:
                print(f"{name}")
        else:
            print("No torrents would be pruned from client.")


class PruneClientCommand(Command):
    def __init__(self, service: PruneService):
        self.service = service

    def run(self) -> PruneClientResult:
        missing_torrent_names_by_id: Mapping[
            int, str
        ] = self.service.get_torrent_name_by_id_with_missing_data()
        for torrent_id in missing_torrent_names_by_id.keys():
            self.service.remove_torrent(torrent_id)
        return PruneClientResult(set(missing_torrent_names_by_id.values()))

    def dry_run(self) -> PruneClientResult:
        missing_torrent_names_by_id: Mapping[
            int, str
        ] = self.service.get_torrent_name_by_id_with_missing_data()
        return PruneClientResult(set(missing_torrent_names_by_id.values()))
