from docopt import docopt


def test_parsing():
    doc_string = """ Add torrents to Transmission (with or without data).

    Usage:
        clutchless add [--dry-run] [--delete] [-f | --force] <paths> ... [-d <data> ...]

    Arguments:
        <paths>  Paths to metainfo files (.torrent) to add to Transmission.

    Options:
        -d <data> ...   Data to associate to torrents.
        -f, --force     Add torrents even when they're not found.
        --delete        Delete successfully added torrents (meaningless when used with --dry-run).
        --dry-run       Output what would be done instead of modifying anything.
    """
    argv = ["add", "test", "hi", "-d", "hmm"]
    parsed = docopt(doc=doc_string, argv=argv)
    assert parsed["-d"] == ["hmm"]
    assert parsed["<paths>"] == ["test", "hi"]
