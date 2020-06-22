""" Clean up things in different contexts (files, torrents, etc.).

Usage:
    clutchless prune <command> [<args> ...]

The available prune commands are:
    folder  Removes .torrent files that are associated with torrents registered in Transmission.
    client  Removes torrents without data from Transmission (error code 3: data no longer found at original location).
"""
