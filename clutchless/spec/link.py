""" For torrents with missing data in Transmission, find the data and set the found location.

Usage:
    clutchless link [--dry-run] (<data> ...)
    clutchless link --list

Arguments:
    <data> ...  Path(s) of directories to search for already-downloaded data.

Options:
    --dry-run   Prevent any changes in Transmission, only report found data for 0% data torrents.
    --list      Output all torrents with 0% completion.
"""
