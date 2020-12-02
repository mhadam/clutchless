""" Migrate torrents to a new location, sorting them into separate folders for each tracker.

Usage:
    clutchless organize [--dry-run] <destination> [-t <trackers>] [-d <folder>]
    clutchless organize --list

Arguments:
    <destination>   Directory where torrents will be sorted into separate folders for each tracker.

Options:
    --list          Output all trackers with their ID for use in `-t` option.
    -t <trackers>   Specify a folder name for a tracker, takes the format <0=folder;1,3=folder2;...> - use quotes!
    -d <folder>     Specify the default folder name for trackers that aren't specified or found.
    --dry-run       Prevent any changes in Transmission, only report found data for 0% data torrents.
"""
from collections import UserDict
from typing import Mapping, Sequence, Set, Iterable


def any_duplicates(iterable: Iterable) -> bool:
    seen = set()
    for x in iterable:
        if x in seen:
            return True
        seen.add(x)
    return False


class SpecError(Exception):
    def __init__(self, message):
        self.message = message


class FolderAssignment:
    def __init__(self, value: str):
        self.value = value
        self._validate()

    @property
    def indices(self) -> Set[int]:
        raw_indices = self._split_parts[0]
        indices = [int(ind) for ind in raw_indices.split(",")]
        if any_duplicates(indices):
            raise SpecError("duplicate index specified")
        return set(indices)

    @property
    def folder(self) -> str:
        return self._split_parts[1]

    @property
    def _split_parts(self) -> Sequence[str]:
        return self.value.split("=")

    def _validate(self):
        self._validate_folder_name(self.folder)
        self._validate_split_parts(self._split_parts)
        self._validate_indices()

    @staticmethod
    def _validate_folder_name(folder_name: str):
        if not all(ch.isalnum() for ch in folder_name):
            raise SpecError(f"{folder_name} needs to be alphanumeric")
        if len(folder_name) == 0:
            raise SpecError(f"folder name is empty")

    @staticmethod
    def _validate_split_parts(option: Sequence[str]):
        if len(option) > 2:
            raise (SpecError(f"{option} needs to be properly delimited"))
        if any(part == "" for part in option):
            raise (SpecError(f"empty string in option: {option}"))

    def _validate_indices(self):
        try:
            _ = self.indices
        except ValueError:
            raise SpecError(f"{self._split_parts[0]} is not an integer.")


class TrackerSpec(UserDict, Mapping[int, str]):
    """
    Separate options are delimited by a semicolon and option keys are delimited with a comma.
    Terminating with a delimiter is acceptable (it's the same as no delimiter).
    For example, torrents with tracker id 1 and 2 are organized into Folder1, id 3 into Folder2:
    1,2=Folder1;3=Folder2
    """

    def __init__(self, value: str):
        super().__init__()
        self.value = value
        merged_assignments = self._merge(self.assignments)
        self.update(merged_assignments)

    @staticmethod
    def _merge(assignments: Iterable[FolderAssignment]) -> Mapping[int, str]:
        result = {}
        for assignment in assignments:
            for index in assignment.indices:
                if index in result:
                    raise SpecError(f"{index} is a duplicate index.")
                result[index] = assignment.folder
        return result

    @property
    def assignments(self) -> Iterable[FolderAssignment]:
        raw_assignments: Sequence[str] = self.value.rstrip(";").split(";")
        for value in raw_assignments:
            yield FolderAssignment(value)
