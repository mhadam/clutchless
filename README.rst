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

.. image:: https://coveralls.io/repos/github/mhadam/clutchless/badge.svg
    :target: https://coveralls.io/github/mhadam/clutchless

Other links
===========

* `Developer documentation`_

Quick start
===========

Install the package:

.. code-block:: console

    $ pip install clutchless

The ``-h`` flag can be used to bring up documentation, e.g. ``clutchless -h``::

    A tool for working with torrents and their data in the Transmission BitTorrent client.

    Usage:
        clutchless [options] [-v ...] <command> [<args> ...]

    Options:
        -a <address>, --address <address>   Address for Transmission (default is http://localhost:9091/transmission/rpc).
        -h, --help  Show this screen.
        -v, --verbose   Verbose terminal output (multiple -v increase verbosity).

    The available clutchless commands are:
        add         Add metainfo files to Transmission (with or without data).
        find        Locate data that belongs to metainfo files.
        link        For torrents with missing data in Transmission, find the data and set the location.
        archive     Copy metainfo files from Transmission for backup.
        organize    Migrate torrents to a new location, sorting them into separate folders for each tracker.
        prune       Clean up things in different contexts (files, torrents, etc.).
        dedupe      Delete duplicate metainfo files from paths.
        rename      Changes the name of metainfo files based on metainfo (torrent name and info hash).

    See 'clutchless help <command>' for more information on a specific command.

Examples
========

To copy all the metainfo files (``.torrent``) in Transmission to ``~/torrent_archive``::

    clutchless archive ~/torrent_archive


To add some torrents to Transmission, searching ``~/torrent_archive`` for metainfo files and finding data in
``~/torrent_data``::

    clutchless add ~/torrent_archive -d ~/torrent_data

To look for matching data given a search folder (``~/torrent_data``) and a directory (``~/torrent_files``)
that contains metainfo files::

    clutchless find ~/torrent_files -d ~/torrent_data


To organize torrents into folders under ``~/new_place`` and named by tracker, with ``default_folder`` for ones missing
a folder name for one reason or another::

    clutchless organize ~/new_place -d default_folder

Remove torrents that are completely missing data::

    clutchless prune client

Remove metainfo files from some folders (``folder1``, ``folder2``) that are found in Transmission::

    clutchless prune folder ~/folder1 ~/folder2

To associate torrent to their matching data found in any number of folders (in this case just two)::

    clutchless link ~/data_folder_1 ~/data_folder_2

To delete duplicate metainfo files in ``~/folder1``::

    clutchless dedupe ~/folder1

To rename all the metainfo files in ``~/folder1`` according to metainfo (format: ``torrent_name.hash.torrent``)::

    clutchless rename ~/folder1

.. _developer documentation: DEVELOPER.rst
