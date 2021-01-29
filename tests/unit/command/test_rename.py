from pathlib import Path
from typing import Set, Mapping

from clutchless.command.rename import (
    select,
    RenameCommand,
    get_hash,
    get_clashing_renames,
)
from clutchless.domain.torrent import MetainfoFile
from tests.mock_fs import MockFilesystem


def test_select():
    original = MetainfoFile({"info_hash": "arbitrary"}, path=Path("/some/file1"))
    dupe = MetainfoFile({"info_hash": "arbitrary"}, path=Path("/some/file2"))
    second_dupe = MetainfoFile({"info_hash": "arbitrary"}, path=Path("/some/file3"))
    dupes = {Path("/some/new_name"): {original, dupe, second_dupe}}

    result: Mapping[MetainfoFile, Set[MetainfoFile]] = select(dupes)

    assert result == {original: {dupe, second_dupe}}


def test_get_hash():
    s = {MetainfoFile(properties={"info_hash": "arbitrary"})}

    result = get_hash(s)

    assert result == "arbitrary"


def test_get_clashing_renames():
    unique = MetainfoFile(
        properties={"name": "file1", "info_hash": "a" * 16}, path=Path("/file1")
    )
    first_clashing = MetainfoFile(
        properties={"name": "file2", "info_hash": "b" * 16}, path=Path("/file2")
    )
    second_clashing = MetainfoFile(
        properties={"name": "file2", "info_hash": "b" * 16}, path=Path("/file3")
    )
    files = [unique, first_clashing, second_clashing]

    clashing, not_clashing = get_clashing_renames(files)

    assert clashing == {"b" * 16: {first_clashing, second_clashing}}
    assert not_clashing == {unique}


def test_rename_command_dry_run():
    original = MetainfoFile(
        {"info_hash": "arbitrary", "name": "some_name"},
        path=Path("/some/some_name.arbitrary.torrent"),
    )
    dupe = MetainfoFile(
        {"info_hash": "arbitrary", "name": "some_name"}, path=Path("/some/file1")
    )
    second_dupe = MetainfoFile(
        {"info_hash": "arbitrary", "name": "some_name"}, path=Path("/some/file2")
    )
    files = [original, dupe, second_dupe]
    fs = MockFilesystem({"some": ["some_name.arbitrary.torrent", "file1", "file2"]})
    command = RenameCommand(fs, files)

    output = command.dry_run()

    assert len(output.others_by_selected) == 1
    selected, others = next(iter(output.others_by_selected.items()))

    assert selected in {dupe, second_dupe}
    other_dupe = next(iter(others))
    assert other_dupe in {dupe, second_dupe}
    assert select != other_dupe

    assert output.new_name_by_existing_file == {
        selected: "some_name.arbitrary.torrent",
    }
    assert output.new_name_by_actionable_file == {}
