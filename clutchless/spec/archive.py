""" Copy metainfo files from Transmission for backup.

Usage:
    clutchless archive [--dry-run] [--errors] <destination>

Arguments:
    <destination>   Directory where metainfo files in Transmission will be copied.

Options:
    --errors        Moves files into folders below the archive directory according to their error code.
    --dry-run       Do not copy any files, only list which files would be moved.
"""
