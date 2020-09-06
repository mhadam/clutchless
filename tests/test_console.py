from clutchless.console import CommandCreator
from clutchless.subcommand.find import FindCommand
from clutchless.subcommand.other import InvalidCommand
from clutchless.transmission import TransmissionApi

COMMAND_KEY = "<command>"
ARGS_KEY = "<args>"


def test_create_find(mocker):
    args = {
        COMMAND_KEY: "find",
        ARGS_KEY: ['some_arg', '-d', 'some_dir']
    }
    client = mocker.Mock(spec=TransmissionApi)
    creator = CommandCreator(args, client)

    command = creator.get_command()

    assert isinstance(command, FindCommand)


def test_create_invalid(mocker):
    args = {
        COMMAND_KEY: "obviously_invalid",
        ARGS_KEY: ['some_arg', '-d', 'some_dir']
    }
    client = mocker.Mock(spec=TransmissionApi)
    creator = CommandCreator(args, client)

    command = creator.get_command()

    assert isinstance(command, InvalidCommand)
