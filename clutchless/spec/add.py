""" Add torrents to Transmission (with or without data).

Usage:
    clutchless add [--dry-run] [--delete] [-f | --force] (<metainfo> ...) [-d <data> ...]

Arguments:
    <metainfo> ...  Paths to metainfo files (files or directories) to add to Transmission.

Options:
    -d <data> ...   Data to associate to torrents.
    -f, --force     Add torrents even when they're not found.
    --delete        Delete successfully added torrents (meaningless when used with --dry-run).
    --dry-run       Output what would be done instead of modifying anything.
"""
