""" Migrate torrents to a new location, sorting them into separate folders for each tracker.

Usage:
    clutchless organize [--dry-run] <location> [-t <tracker_id=folder_name> ...]
    clutchless organize --list

Arguments:
    <location>  Directory where torrents will be sorted into separate folders for each tracker.

Options:
    --list  Output all trackers with their ID for use in `-t` option.
    -t <tracker_id=folder_name> ... Specify a folder name for a tracker.
    --dry-run   Prevent any changes in Transmission, only report found data for incomplete torrents.
"""
