""" Remove .torrent files from folders, but only if they're associated with torrents registered in Transmission.

Usage:
    clutchless prune folder [--dry-run] <folders> ...

Arguments:
    <folders> ...   Folders to search for .torrent files to remove.

Options:
    --dry-run   Doesn't delete any files, only outputs what would be done.

"""
