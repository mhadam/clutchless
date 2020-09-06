from clutchless.console import prune_factory
from clutchless.subcommand.other import MissingCommand
from clutchless.subcommand.prune.client import PruneClientCommand
from clutchless.subcommand.prune.folder import PruneFolderCommand
from clutchless.transmission import TransmissionApi


def test_prune_factory_folder(mocker):
    argv = ['prune', 'folder']
    client = mocker.Mock(spec=TransmissionApi)

    result = prune_factory(argv, client)

    assert isinstance(result, PruneFolderCommand)


def test_prune_factory_client(mocker):
    argv = ['prune', 'client']
    client = mocker.Mock(spec=TransmissionApi)

    result = prune_factory(argv, client)

    assert isinstance(result, PruneClientCommand)


def test_prune_factory_missing(mocker):
    argv = ['prune', 'invalid']
    client = mocker.Mock(spec=TransmissionApi)

    result = prune_factory(argv, client)

    assert isinstance(result, MissingCommand)
