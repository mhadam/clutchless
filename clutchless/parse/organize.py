""" Migrate torrents to a new location, sorting them into separate folders for each tracker.

Usage:
    clutchless organize [--dry-run] <location> [-t <trackers>] [-d <folder>]
    clutchless organize --list

Arguments:
    <location>  Directory where torrents will be sorted into separate folders for each tracker.

Options:
    --list          Output all trackers with their ID for use in `-t` option.
    -t <trackers>   Specify a folder name for a tracker, takes the format <id=folder;id2,id3=folder2;...> - use quotes!
    -d <folder>     Specify the default folder name for trackers that aren't specified or found.
    --dry-run       Prevent any changes in Transmission, only report found data for incomplete torrents.
"""
from collections import UserDict
from dataclasses import dataclass
from typing import Mapping, MutableMapping, Sequence, Set


def any_duplicates(sequence: Sequence):
    seen = set()
    for x in sequence:
        if x in seen:
            return True
        seen.add(x)
    return False


class SpecError(Exception):
    def __init__(self, message):
        self.message = message


@dataclass
class FolderAssignment:
    indices: Set[int]
    folder: str


class FolderAssignmentParser:
    def __init__(self):
        pass

    def parse(self, raw_input: str) -> FolderAssignment:
        split_parts = self.__get_valid_split_parts(raw_input)
        try:
            return self.__handle_split_parts(split_parts)
        except ValueError:
            raise SpecError(f"{split_parts[0]} is not an integer.")

    def __get_valid_split_parts(self, option: str) -> Sequence[str]:
        split_option = option.split("=")
        self.__validate_split_parts(split_option)
        return split_option

    def __handle_split_parts(self, option: Sequence[str]) -> FolderAssignment:
        raw_indices, folder_name = option
        self.__validate_folder_name(folder_name)
        indices = self.__coerce_indices(raw_indices)
        return FolderAssignment(indices, folder_name)

    def __coerce_indices(self, raw_indices: str) -> Set[int]:
        indices = [int(ind) for ind in raw_indices.split(",")]
        if any_duplicates(indices):
            raise SpecError("Duplicate index specified")
        return set(indices)

    def __validate_folder_name(self, folder_name: str):
        if not all(ch.isalnum() for ch in folder_name):
            raise SpecError(f"{folder_name} needs to be only alphanumeric.")
        if len(folder_name) == 0:
            raise SpecError(f"Folder name is empty.")

    def __validate_split_parts(self, option: Sequence[str]):
        if len(option) > 2:
            raise (SpecError(f"{option} needs to be delimited."))
        if any(part == "" for part in option):
            raise (SpecError(f"Empty string in option: {option}"))


class TrackerSpec(UserDict, MutableMapping[int, str]):
    """{index : folder name}"""

    pass


class TrackerSpecParser:
    """
    Separate options are delimited by a semicolon and option keys are delimited with a comma.
    Terminating with a delimiter is acceptable (it's the same as no delimiter).
    For example, torrents with tracker id 1 and 2 are organized into Folder1, id 3 into Folder2:
    1,2=Folder1;3=Folder2
    """

    def __init__(self):
        pass

    def parse(self, raw_input: str) -> TrackerSpec:
        merged_assignments = self.__merge_options(raw_input)
        return TrackerSpec(merged_assignments)

    def __merge_options(self, raw_input: str) -> Mapping[int, str]:
        result = {}
        for assignment in self.__parse_assignments(raw_input):
            for index in assignment.indices:
                self.__validate_duplicate_index_name(result, index)
                result[index] = assignment.folder
        return result

    def __parse_assignments(self, raw_input: str) -> Sequence[FolderAssignment]:
        raw_assignments: Sequence[str] = raw_input.rstrip(";").split(";")
        for assignment in raw_assignments:
            yield FolderAssignmentParser().parse(assignment)

    def __validate_duplicate_index_name(self, result: Mapping[int, str], index: int):
        if index in result:
            raise SpecError(f"{index} is a duplicate index.")
