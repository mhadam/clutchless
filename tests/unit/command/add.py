from pytest_mock import MockerFixture

from clutchless.command.add import AddCommand
from clutchless.external.filesystem import Filesystem
from clutchless.external.transmission import TransmissionApi


def test_add_torrents(mocker: MockerFixture):
    fs = mocker.Mock(spec=Filesystem)
    api = mocker.Mock(spec=TransmissionApi)

    command = AddCommand(fs)
    command.run()
