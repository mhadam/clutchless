from os.path import abspath
from pathlib import Path

import pytest

from clutchless.torrent import MetainfoFile


def test_metainfo_file_load():
    integration_package_path = Path(abspath(__file__)).parent
    torrent_file_path = Path(integration_package_path, 'assets/being_earnest.torrent')
    data_path = Path(integration_package_path, 'assets/data')

    metainfo_file = MetainfoFile.from_path(torrent_file_path)

    assert metainfo_file.is_located_at_path(data_path)


def test_metainfo_with_multiple_file():
    integration_package_path = Path(abspath(__file__)).parent
    torrent_file_path = Path(integration_package_path, 'assets/being_earnest.torrent')

    metainfo_file = MetainfoFile.from_path(torrent_file_path)

    assert not metainfo_file.is_single_file


def test_metainfo_with_single_file():
    integration_package_path = Path(abspath(__file__)).parent
    torrent_file_path = Path(integration_package_path, 'assets/ion.torrent')

    metainfo_file = MetainfoFile.from_path(torrent_file_path)

    assert metainfo_file.is_single_file


def test_metainfo_with_invalid_file():
    integration_package_path = Path(abspath(__file__)).parent
    torrent_file_path = Path(integration_package_path, 'assets/ion.torrent')

    metainfo_file = MetainfoFile(
        torrent_file_path,
        {
            'info': {
                'length': '',
                'files': ''
            }
        }
    )

    with pytest.raises(Exception) as e:
        metainfo_file.is_single_file
    assert "must contain either length key or files key" in str(e.value)
