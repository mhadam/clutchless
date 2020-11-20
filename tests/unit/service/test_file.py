from collections import defaultdict
from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.domain.torrent import MetainfoFile
from clutchless.external.filesystem import Filesystem, FileLocator
from clutchless.external.metainfo import MetainfoReader
from clutchless.service.file import collect_metainfo_files, collect_metainfo_paths


def test_collect_metainfo_files(mocker: MockerFixture):
    raw_paths = {
        Path("/some_path"),
        Path("/another_path/file.torrent"),
    }

    files = {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
        Path("/some_path/child1/file3"),
    }

    directories = {
        Path("/another_path"),
        Path("/some_path/child1"),
        Path("/some_path"),
    }

    children = defaultdict(
        set,
        {
            Path("/some_path"): {Path("/some_path/child1")},
            Path("/some_path/child1"): {
                Path("/some_path/child1/file2.torrent"),
                Path("/some_path/child1/file3"),
            },
        },
    )

    filesystem = mocker.Mock(spec=Filesystem)
    filesystem.exists.side_effect = lambda path: path in files or path in directories
    filesystem.is_file.side_effect = lambda path: path in files
    filesystem.is_directory.side_effect = lambda path: path in directories
    filesystem.children.side_effect = lambda path: children.get(path)

    locator = mocker.Mock(spec=FileLocator)
    locator.collect.return_value = {Path("/some_path/child1/file2.torrent")}

    reader = mocker.Mock(spec=MetainfoReader)
    reader.from_path.side_effect = lambda path: MetainfoFile({"info_hash": path})

    result_files = collect_metainfo_files(filesystem, locator, raw_paths, reader)
    result_paths = collect_metainfo_paths(filesystem, locator, raw_paths)

    assert set(result_paths) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }

    assert len(result_files) == 2
