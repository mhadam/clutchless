from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.organize import (
    ListOrganizeCommandOutput,
    OrganizeCommand,
    OrganizeAction,
)
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
