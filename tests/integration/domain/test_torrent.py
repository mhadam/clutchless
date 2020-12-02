from clutchless.external.filesystem import DefaultFilesystem
from clutchless.external.metainfo import (
    DefaultMetainfoReader,
    MetainfoReader,
    DefaultTorrentDataReader,
)


def test_metainfo_multifile_load(datadir):
    metainfo_reader: MetainfoReader = DefaultMetainfoReader()
    metainfo_path = datadir / "being_earnest.torrent"
    metainfo_file = metainfo_reader.from_path(metainfo_path)

    fs = DefaultFilesystem()
    data_reader = DefaultTorrentDataReader(fs)
    result = data_reader.verify(datadir, metainfo_file)

    assert result


def test_metainfo_singlefile_load(datadir):
    metainfo_reader: MetainfoReader = DefaultMetainfoReader()
    metainfo_path = datadir / "ion.torrent"
    metainfo_file = metainfo_reader.from_path(metainfo_path)

    fs = DefaultFilesystem()
    data_reader = DefaultTorrentDataReader(fs)
    result = data_reader.verify(datadir, metainfo_file)

    assert result
