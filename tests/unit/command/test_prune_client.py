from pytest_mock import MockerFixture

from clutchless.command.prune.client import PruneClientCommand
from clutchless.service.torrent import PruneService


def test_prune_client_run(mocker: MockerFixture):
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_name_by_id_with_missing_data.return_value = {
        1: "some_name"
    }
    command = PruneClientCommand(service)

    command.run()

    service.remove_torrent.assert_called_once_with(1)


def test_prune_client_run_output(mocker: MockerFixture, capsys):
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_name_by_id_with_missing_data.return_value = {
        1: "some_name"
    }
    command = PruneClientCommand(service)

    output = command.run()
    output.display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "The following torrents were pruned:",
        "some_name"
    ]) + "\n"


def test_prune_client_dry_run(mocker: MockerFixture):
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_name_by_id_with_missing_data.return_value = {
        1: "some_name"
    }
    command = PruneClientCommand(service)

    command.dry_run()

    service.remove_torrent.assert_not_called()


def test_prune_client_dry_run_output(mocker: MockerFixture, capsys):
    service: PruneService = mocker.Mock(spec=PruneService)
    service.get_torrent_name_by_id_with_missing_data.return_value = {
        1: "some_name"
    }
    command = PruneClientCommand(service)

    output = command.dry_run()
    output.dry_run_display()

    result = capsys.readouterr().out
    assert result == "\n".join([
        "The following torrents would be pruned:",
        "some_name"
    ]) + "\n"
