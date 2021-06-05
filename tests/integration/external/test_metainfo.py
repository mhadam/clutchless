import pytest

from clutchless.external.filesystem import DefaultFilesystem
from clutchless.external.metainfo import (
    DefaultMetainfoIO,
    MetainfoIO,
    DefaultTorrentDataLocator,
    TorrentData,
)


@pytest.mark.asyncio
async def test_async_data_locator_multi_file(datadir):
    reader: MetainfoIO = DefaultMetainfoIO()
    path = datadir / "being_earnest.torrent"
    file = reader.from_path(path)

    fs = DefaultFilesystem()
    locator = DefaultTorrentDataLocator(fs, datadir)
    result = await locator.find(file)

    assert result == TorrentData(file, datadir)
