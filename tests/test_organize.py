from pytest import raises

from clutchless.parse.organize import TrackerSpecParser, FolderAssignmentParser, FolderAssignment, \
    SpecError
from clutchless.subcommand.organize import HostnameFormatter, FolderNameGrouper, FolderNameUrls, FolderNameChooser


def test_format_hostname():
    tracker = "http://sometracker.tv/e2ea2131f9c7b55272e39085c9d85884/announce"

    formatted_hostname = HostnameFormatter.format(tracker)

    assert formatted_hostname == "SometrackerTv"


def test_spec_parse():
    raw_spec = "1,2=Folder1;3=Folder2"
    parser = TrackerSpecParser()

    parsed_spec = parser.parse(raw_spec)

    assert parsed_spec == {
        1: "Folder1",
        2: "Folder1",
        3: "Folder2"
    }


def test_assignment_parse_with_multiple_indices():
    raw_assignment = "1,2=Folder1"
    parser = FolderAssignmentParser()

    parsed_assignment = parser.parse(raw_assignment)

    assert parsed_assignment == FolderAssignment(
        indices={1, 2},
        folder='Folder1'
    )


def test_assignment_parse_with_single_index():
    raw_assignment = "3=Folder2"
    parser = FolderAssignmentParser()

    parsed_assignment = parser.parse(raw_assignment)

    assert parsed_assignment == FolderAssignment(
        indices={3},
        folder='Folder2'
    )


def test_assignment_parse_with_duplicate_indices():
    raw_assignment = "3,3=Folder2"
    parser = FolderAssignmentParser()

    with raises(SpecError) as e:
        parser.parse(raw_assignment)

    assert "duplicate" in str(e.value).lower()


def test_get_response_tracker_map(mocker):
    first_announce = "http://hi.thisisatesttracker.me:1950/b6840b78127ec583cd2abd0f80edb75d/announce"
    second_announce = "http://hi.thisisatesttracker.me:1950/777580bca8824093141c767c339013ab/announce"
    urls = {first_announce, second_announce}
    client = mocker.MagicMock()
    client.get_announce_urls.return_value = urls

    response_map = FolderNameGrouper(client).get_folder_name_to_announce_urls()

    assert response_map == {
        'ThisisatesttrackerMe': urls
    }


def test_get_ordered_tracker_list(mocker):
    first_announce = "http://hi.thisisatesttracker.me:1950/b6840b78127ec583cd2abd0f80edb75d/announce"
    second_announce = "http://hi.thisisatesttracker.me:1950/777580bca8824093141c767c339013ab/announce"
    urls = {first_announce, second_announce}
    client = mocker.MagicMock()
    client.get_announce_urls.return_value = urls
    tracker_list = FolderNameGrouper(client)

    result = tracker_list.get_ordered_folder_name_to_announce_urls()

    assert result == [
        FolderNameUrls(
            folder_name='ThisisatesttrackerMe',
            announce_urls=urls
        )
    ]


def test_get_tracker_folder_map(mocker):
    first_announce = "http://hi.thisisatesttracker.me:1950/b6840b78127ec583cd2abd0f80edb75d/announce"
    second_announce = "http://hi.thisisatesttracker.me:1950/777580bca8824093141c767c339013ab/announce"
    urls = {first_announce, second_announce}
    client = mocker.MagicMock()
    client.get_announce_urls.return_value = urls
    tracker_list = FolderNameChooser(client)

    result = tracker_list.get_announce_url_to_folder_name()

    folder_name = 'ThisisatesttrackerMe'
    assert result == {
        first_announce: folder_name,
        second_announce: folder_name
    }
