from pathlib import Path

from clutchless.command.dedupe import DedupeCommand
from clutchless.domain.torrent import MetainfoFile
from tests.mock_fs import MockFilesystem


def test_dry_run():
    files = [
        MetainfoFile({"name": "some_name", "info_hash": "aaa"}, Path("/some/path")),
        MetainfoFile({"name": "some_name", "info_hash": "aaa"}, Path("/some/path2"))
    ]
    fs = MockFilesystem({})
    command = DedupeCommand(fs, files)

    output = command.dry_run()

    # can't guarantee how files are selected hence the messy assertions
    assert len(output.deleted_files_by_hash) == 1
    deleted_file = output.deleted_files_by_hash['aaa'].pop()
    assert deleted_file in files
    assert len(output.remaining_files) == 1
    remaining_file = output.remaining_files.pop()
    assert remaining_file in files
    assert remaining_file != deleted_file


def test_run():
    files = [
        MetainfoFile({"name": "some_name", "info_hash": "aaa"}, Path("/some/path")),
        MetainfoFile({"name": "some_name", "info_hash": "aaa"}, Path("/some/path2"))
    ]
    fs = MockFilesystem({"some": ['path', 'path2']})
    command = DedupeCommand(fs, files)

    output = command.run()

    # can't guarantee how files are selected hence the messy assertions
    assert len(output.deleted_files_by_hash) == 1
    deleted_file = output.deleted_files_by_hash['aaa'].pop()
    assert deleted_file in files
    assert len(output.remaining_files) == 1
    remaining_file = output.remaining_files.pop()
    assert remaining_file in files
    assert remaining_file != deleted_file
