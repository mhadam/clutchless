from pathlib import Path

from pytest_mock import MockerFixture

from clutchless.command.find import FindCommand
from clutchless.domain.torrent import LinkedMetainfo, MetainfoFile
from clutchless.external.filesystem import Filesystem
from clutchless.service.torrent import LinkService
from clutchless.spec.find import FindArgs


def test_find_found(mocker: MockerFixture):
    metainfo_path = Path('/', 'metainfo.torrent')
    search_path = Path('/', 'data')
    properties = {
        'info_hash': 'meaningless and necessary',
        'name': 'test_name',
        'info': {
            'length': 0
        }
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    fs = mocker.Mock(spec=Filesystem)
    fs.find.return_value = Path('/', 'data', 'test_name')
    find_args = FindArgs({}, fs)
    link_service = LinkService(fs, {search_path})

    command = FindCommand(find_args, link_service, {metainfo_file})
    output = command.run()

    assert output.found == {LinkedMetainfo(metainfo_file, search_path)}


def test_find_missing(mocker: MockerFixture):
    metainfo_path = Path('/', 'metainfo.torrent')
    search_path = Path('/', 'data')
    properties = {
        'info_hash': 'meaningless and necessary',
        'name': 'test_name',
        'info': {
            'length': 0
        }
    }
    metainfo_file = MetainfoFile(properties, metainfo_path)
    fs = mocker.Mock(spec=Filesystem)
    fs.find.return_value = None
    find_args = FindArgs({}, fs)
    link_service = LinkService(fs, {search_path})

    command = FindCommand(find_args, link_service, {metainfo_file})
    output = command.run()

    assert output.found == set()
    assert output.missing == {metainfo_file}
