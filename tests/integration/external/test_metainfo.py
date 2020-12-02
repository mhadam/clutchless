from clutchless.external.filesystem import DefaultFilesystem
from clutchless.external.metainfo import (
    DefaultMetainfoReader,
    MetainfoReader,
    AsyncTorrentDataLocator,
)


def test_async_data_locator_multi_file(datadir):
    metainfo_reader: MetainfoReader = DefaultMetainfoReader()
    metainfo_path = datadir / "being_earnest.torrent"
    metainfo_file = metainfo_reader.from_path(metainfo_path)

    fs = DefaultFilesystem()
    locator = AsyncTorrentDataLocator(fs, {datadir})
    result = locator.find({metainfo_file})

    assert len(result) == 1
    assert result.pop().location == datadir
