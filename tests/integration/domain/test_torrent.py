from clutchless.domain.torrent import MetainfoFile

from clutchless.external.filesystem import DefaultFilesystem


def test_metainfo_multifile_load(datadir):
    metainfo_path = (datadir / 'being_earnest.torrent')
    metainfo_file = MetainfoFile.from_path(metainfo_path)

    fs = DefaultFilesystem()

    result = metainfo_file.verify(fs, datadir)

    assert result


def test_metainfo_singlefile_load(datadir):
    metainfo_path = (datadir / 'ion.torrent')
    metainfo_file = MetainfoFile.from_path(metainfo_path)

    fs = DefaultFilesystem()

    result = metainfo_file.verify(fs, datadir)

    assert result
