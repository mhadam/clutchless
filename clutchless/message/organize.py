from typing import Sequence

from texttable import Texttable

from clutchless.subcommand.organize import OrganizeTracker


def print_tracker_list(tracker_list: Sequence[OrganizeTracker]):
    if len(tracker_list) > 0:
        table = Texttable()
        table.add_row(["ID", "Folder name", "Addresses"])
        for tracker in tracker_list:
            table.add_row([tracker.index, tracker.netloc, tracker.addresses])
        print(table.draw())
