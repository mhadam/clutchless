""" Remove metainfo files in folders, only if they're associated with torrents registered in Transmission.

Usage:
    clutchless prune folder [--dry-run] <metainfo> ...

Arguments:
    <metainfo> ...  Folders to search for metainfo files to remove.

Options:
    --dry-run       Doesn't delete any files, only outputs what would be done.

"""
