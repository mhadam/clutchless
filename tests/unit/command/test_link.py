from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.link import LinkCommand, LinkFailure, ListLinkCommand
from clutchless.domain.torrent import MetainfoFile
from clutchless.external.metainfo import TorrentData
from clutchless.service.torrent import LinkService, FindService


def test_link_success(mocker: MockerFixture):
    metainfo_file = MetainfoFile({"info_hash": "meaningless"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    find_service = mocker.Mock(spec=FindService)
    find_service.find.return_value = {TorrentData(metainfo_file, location)}
    command = LinkCommand(link_service, find_service)

    output = command.run()

    assert output.success == [TorrentData(metainfo_file, location)]


def test_link_no_matching_data(mocker: MockerFixture):
    metainfo_file = MetainfoFile({"info_hash": "meaningless"})

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    find_service = mocker.Mock(spec=FindService)
    find_service.find.return_value = {TorrentData(metainfo_file)}
    command = LinkCommand(link_service, find_service)

    output = command.run()

    assert output.success == []
    assert output.no_matching_data == {metainfo_file}


def test_link_failure(mocker: MockerFixture):
    metainfo_file = MetainfoFile({"info_hash": "meaningless"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    link_service.change_location.side_effect = RuntimeError("something")
    find_service = mocker.Mock(spec=FindService)
    torrent_data = TorrentData(metainfo_file, location)
    find_service.find.return_value = {torrent_data}
    command = LinkCommand(link_service, find_service)

    output = command.run()

    assert output.success == []
    assert output.no_matching_data == set()
    assert output.fail == [LinkFailure(torrent_data, "something")]


def test_link_run_failure_output(mocker: MockerFixture, capsys):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    link_service.change_location.side_effect = RuntimeError("something")
    find_service = mocker.Mock(spec=FindService)
    torrent_data = TorrentData(metainfo_file, location)
    missing_torrent_data = TorrentData(metainfo_file)
    find_service.find.return_value = {torrent_data, missing_torrent_data}
    command = LinkCommand(link_service, find_service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Couldn't find the data for the following torrents:",
        "some_name",
        "Failed to link the following torrents:",
        "some_name because: something",
    ]) + "\n"


def test_link_dry_run_failure_output(mocker: MockerFixture, capsys):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    link_service.change_location.side_effect = RuntimeError("something")
    find_service = mocker.Mock(spec=FindService)
    torrent_data = TorrentData(metainfo_file, location)
    missing_torrent_data = TorrentData(metainfo_file)
    find_service.find.return_value = {torrent_data, missing_torrent_data}
    command = LinkCommand(link_service, find_service)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Found the following torrents:",
        "some_name at .",
        "Couldn't find data for the following torrents:",
        "some_name"
    ]) + "\n"


def test_link_run_success_output(mocker: MockerFixture, capsys):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    find_service = mocker.Mock(spec=FindService)
    find_service.find.return_value = {TorrentData(metainfo_file, location)}
    command = LinkCommand(link_service, find_service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Linked the following torrents:",
        "some_name at ."
    ]) + "\n"


def test_link_dry_run_success_output(mocker: MockerFixture, capsys):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    location = Path()

    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    find_service = mocker.Mock(spec=FindService)
    find_service.find.return_value = {TorrentData(metainfo_file, location)}
    command = LinkCommand(link_service, find_service)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Found the following torrents:",
        "some_name at ."
    ]) + "\n"


def test_link_list_run(mocker:MockerFixture):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    command = ListLinkCommand(link_service)

    output = command.run()

    assert output.files == {metainfo_file}


def test_link_list_output(mocker: MockerFixture, capsys):
    metainfo_file = MetainfoFile({"info_hash": "meaningless", "name": "some_name"})
    link_service = mocker.Mock(spec=LinkService)
    link_service.get_incomplete_id_by_metainfo_file.return_value = {metainfo_file: 1}
    command = ListLinkCommand(link_service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "Found following missing data torrents:",
        "some_name"
    ]) + "\n"
