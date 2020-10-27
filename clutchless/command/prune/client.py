from dataclasses import dataclass, field
from typing import Set

from clutchless.command import Command, CommandResult
from clutchless.external.transmission import TransmissionApi


@dataclass
class PruneClientResult(CommandResult):
    pruned_names: Set[str] = field(default_factory=list)

    def output(self):
        if len(self.pruned_names) > 0:
            print("The following torrents were pruned:")
            for name in self.pruned_names:
                print(f"{name}")
        else:
            print("No torrents were pruned from client.")


class PruneClientCommand(Command):
    def __init__(self, client: TransmissionApi):
        self.client = client

    def run(self) -> CommandResult:
        missing_torrent_names_by_id = (
            self.client.get_torrent_names_by_id_with_missing_data()
        )
        for torrent_id in missing_torrent_names_by_id.keys():
            self.client.remove_torrent_keeping_data(torrent_id)
        return PruneClientResult(set(missing_torrent_names_by_id.values()))


@dataclass
class DryRunPruneClientResult(CommandResult):
    pruned_names: Set[str] = field(default_factory=list)

    def output(self):
        if len(self.pruned_names) > 0:
            print("The following torrents would be pruned:")
            for name in self.pruned_names:
                print(f"{name}")
        else:
            print("No torrents would be pruned from client.")


class DryRunPruneClientCommand(Command):
    def __init__(self, client: TransmissionApi):
        self.client = client

    def run(self) -> CommandResult:
        missing_torrent_names_by_id = (
            self.client.get_torrent_names_by_id_with_missing_data()
        )
        return DryRunPruneClientResult(set(missing_torrent_names_by_id.values()))
