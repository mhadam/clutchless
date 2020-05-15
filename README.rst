**This is still under active development - use at your own risk!**

Clutchless
----------

.. image:: https://img.shields.io/pypi/v/clutchless.svg
    :target: https://pypi.org/project/clutchless
    :alt: PyPI badge

.. image:: https://img.shields.io/pypi/pyversions/clutchless.svg
    :target: https://pypi.org/project/clutchless
    :alt: PyPI versions badge

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg
    :target: https://github.com/ambv/black
    :alt: Black formatter badge

.. image:: https://img.shields.io/pypi/l/clutchless.svg
    :target: https://en.wikipedia.org/wiki/MIT_License
    :alt: License badge

.. image:: https://img.shields.io/pypi/dm/clutchless.svg
    :target: https://pypistats.org/packages/clutchless
    :alt: PyPI downloads badge

Quick start
===========

Install the package:

.. code-block:: console

    $ pip install clutchless

The ``-h`` flag can be used to bring up documentation, e.g. ``clutchless -h``::

    A tool for working with torrents and their data in the Transmission BitTorrent client.

    Usage:
        clutchless [options] <command> [<args> ...]

    Options:
        -h, --help  Show this screen.
        --version   Show version.

    The available clutchless commands are:
        add         Add torrents to Transmission (with or without data).
        find        Locate data that belongs to torrent files.
        link        For torrents with missing data in Transmission, find the data and fix the location.
        archive     Copy .torrent files from Transmission for backup.
        organize    Migrate torrents to a new location, sorting them into separate folders for each tracker.

    See 'clutchless help <command>' for more information on a specific command.
