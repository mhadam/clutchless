""" Migrate torrents to a new location, sorting them into separate folders for each tracker.

Usage:
    clutchless organize [--dry-run] <location> [-t <trackers>]
    clutchless organize --list

Arguments:
    <location>  Directory where torrents will be sorted into separate folders for each tracker.

Options:
    --list          Output all trackers with their ID for use in `-t` option.
    -t <trackers>   Specify a folder name for a tracker, takes the format <id=folder;id2,id3=folder2;...> - use quotes!
    --dry-run       Prevent any changes in Transmission, only report found data for incomplete torrents.
"""
from typing import Mapping, MutableMapping


def get_tracker_specs(options: str) -> Mapping[int, str]:
    """
    Separate options are delimited by a semicolon and option keys are delimited with a comma.
    Terminating with a delimiter is acceptable (it's the same as no delimiter).
    For example, torrents with tracker id 1 and 2 are organized into Folder1, id 3 into Folder2:
    1,2=Folder1;3=Folder2
    """
    result: MutableMapping[int, str] = {}
    for option in options.rstrip(";").split(";"):
        split_option = option.split("=")
        if len(split_option) > 2:
            raise (ValueError(f"{option} needs to be delimited."))
        if any(part == "" for part in split_option):
            raise (ValueError(f"Empty string in option: {option}"))
        try:
            for index in [int(ind) for ind in split_option[0].split(",")]:
                folder_name = split_option[1]
                if not all(ch.isalnum() for ch in folder_name):
                    raise ValueError(f"{folder_name} needs to be only alphanumeric.")
                elif len(folder_name) == 0:
                    raise ValueError(f"Folder name is empty.")
                else:
                    if index in result:
                        raise ValueError(f"{index} is a duplicate index.")
                    else:
                        result[index] = folder_name
        except ValueError:
            raise ValueError(f"{split_option[0]} is not an integer.")
    return result
