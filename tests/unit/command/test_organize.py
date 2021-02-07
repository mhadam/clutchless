from collections import OrderedDict
from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.organize import (
    ListOrganizeCommandOutput,
    OrganizeCommand,
    OrganizeAction,
)
from clutchless.domain.torrent import MetainfoFile
from clutchless.service.torrent import OrganizeService


def test_list_organize_output_shorten_url():
    url = "a" * 45
    result = ListOrganizeCommandOutput._shorten_url(url)

    assert result == "a" * 37 + "..."


def test_organize_command_get_folder_name():
    urls = {"http://test.com/announce"}
    announce_url_to_folder_name = {"http://test.com/announce": "folder"}
    folder_name = OrganizeCommand._get_folder_name(urls, announce_url_to_folder_name)

    assert folder_name == "folder"


def test_organize_command_get_folder_name_missing():
    urls = {}
    announce_url_to_folder_name = {"http://test.com/announce": "folder"}
    folder_name = OrganizeCommand._get_folder_name(urls, announce_url_to_folder_name)

    assert folder_name == "other_torrents"


def test_organize(mocker: MockerFixture):
    service = mocker.Mock(spec=OrganizeService)
    command = OrganizeCommand("", Path("/some_path"), service)

    folder_name_by_announce_url = {"http://test.com/announce": "folder_name"}
    announce_urls_by_torrent_id = {1: {"http://test.com/announce"}}

    result = command._make_actions(
        folder_name_by_announce_url, announce_urls_by_torrent_id
    )

    assert list(result) == [OrganizeAction(Path("/some_path/folder_name"), 1)]


def test_organize_run_display(mocker: MockerFixture, capsys):
    service: OrganizeService = mocker.Mock(spec=OrganizeService)
    service.get_announce_urls_by_folder_name.return_value = OrderedDict(
        [
            ("AfakeCom", ["http://afake.com/12gfdxj7j32356/announce"]),
            ("HiWhatUk", ["http://hi.what.uk:2710/n0fbno312o3w4z/announce"]),
        ]
    )
    service.get_announce_urls_by_torrent_id.return_value = {
        1: {"http://afake.com/12gfdxj7j32356/announce"},
        2: {"http://hi.what.uk:2710/n0fbno312o3w4z/announce"},
    }
    names_by_id = {
        1: MetainfoFile(
            {"info_hash": "aaa", "name": "some_name"}, Path("/some_other_path")
        ),
        2: MetainfoFile(
            {"info_hash": "bbb", "name": "another_name"}, Path("/another_path")
        ),
    }
    paths = [Path("/first_torrent"), Path("/second_torrent")]
    service.get_metainfo_file.side_effect = lambda torrent_id: names_by_id[torrent_id]
    service.get_torrent_location.side_effect = lambda torrent_id: paths[torrent_id - 1]
    command = OrganizeCommand("0=SomeFolder", Path("/some_path"), service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    expected = (
        "\n".join(
            [
                "Organized these torrents:",
                "some_name moved from /first_torrent to /some_path/SomeFolder",
                "another_name moved from /second_torrent to /some_path/HiWhatUk",
            ]
        )
        + "\n"
    )
    assert result == expected


def test_organize_run_display_failure(mocker: MockerFixture, capsys):
    service: OrganizeService = mocker.Mock(spec=OrganizeService)
    service.get_announce_urls_by_folder_name.return_value = OrderedDict(
        [
            ("AfakeCom", ["http://afake.com/12gfdxj7j32356/announce"]),
            ("HiWhatUk", ["http://hi.what.uk:2710/n0fbno312o3w4z/announce"]),
        ]
    )
    service.get_announce_urls_by_torrent_id.return_value = {
        1: {"http://afake.com/12gfdxj7j32356/announce"},
        2: {"http://hi.what.uk:2710/n0fbno312o3w4z/announce"},
    }
    names_by_id = {
        1: MetainfoFile(
            {"info_hash": "aaa", "name": "some_name"}, Path("/some_other_path")
        ),
        2: MetainfoFile(
            {"info_hash": "bbb", "name": "another_name"}, Path("/another_path")
        ),
    }
    paths = [Path("/first_torrent"), Path("/second_torrent")]
    service.get_metainfo_file.side_effect = lambda torrent_id: names_by_id[torrent_id]
    service.get_torrent_location.side_effect = RuntimeError("random error")
    command = OrganizeCommand("0=SomeFolder", Path("/some_path"), service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    expected = (
        "\n".join(
            [
                "Failed to organize these torrents:",
                "some_name because of: random error",
                "another_name because of: random error",
            ]
        )
        + "\n"
    )
    assert result == expected


def test_organize_dry_run_display(mocker: MockerFixture, capsys):
    service: OrganizeService = mocker.Mock(spec=OrganizeService)
    service.get_announce_urls_by_folder_name.return_value = OrderedDict(
        [
            ("AfakeCom", ["http://afake.com/12gfdxj7j32356/announce"]),
            ("HiWhatUk", ["http://hi.what.uk:2710/n0fbno312o3w4z/announce"]),
        ]
    )
    service.get_announce_urls_by_torrent_id.return_value = {
        1: {"http://afake.com/12gfdxj7j32356/announce"},
        2: {"http://hi.what.uk:2710/n0fbno312o3w4z/announce"},
    }
    names_by_id = {
        1: MetainfoFile(
            {"info_hash": "aaa", "name": "some_name"}, Path("/some_other_path")
        ),
        2: MetainfoFile(
            {"info_hash": "bbb", "name": "another_name"}, Path("/another_path")
        ),
    }
    paths = [Path("/first_torrent"), Path("/second_torrent")]
    service.get_metainfo_file.side_effect = lambda torrent_id: names_by_id[torrent_id]
    service.get_torrent_location.side_effect = lambda torrent_id: paths[torrent_id - 1]
    command = OrganizeCommand("0=SomeFolder", Path("/some_path"), service)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    expected = (
        "\n".join(
            [
                "Would organize the following torrents:",
                "some_name to /some_path/SomeFolder",
                "another_name to /some_path/HiWhatUk",
            ]
        )
        + "\n"
    )
    assert result == expected


def test_organize_list_display():
    pass
