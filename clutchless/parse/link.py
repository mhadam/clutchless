""" For torrents with missing data in Transmission, find the data and fix the location.

Usage:
    clutchless link [--dry-run] <data> ...
    clutchless link --list

Arguments:
    <data> ...  Filepath(s) of directories to search for already-downloaded data.

Options:
    --dry-run   Prevent any changes in Transmission, only report found data for incomplete torrents.
    --list      Output all torrents with incomplete data.
"""
