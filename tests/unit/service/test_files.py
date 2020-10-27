from collections import defaultdict
from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.external.filesystem import Filesystem
from clutchless.service.files import collect_metainfo_files


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
    filesystem.collect.return_value = {Path("/some_path/child1/file2.torrent")}

    result = collect_metainfo_files(filesystem, raw_paths)

    assert set(result) == {
        Path("/another_path/file.torrent"),
        Path("/some_path/child1/file2.torrent"),
    }
