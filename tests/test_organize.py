from clutch import Client

from clutchless.subcommand.organize import HostnameFormatter, ResponseTrackers


def test_format_hostname():
    tracker = "http://sometracker.tv/e2ea2131f9c7b55272e39085c9d85884/announce"

    formatted_hostname = HostnameFormatter.format(tracker)

    assert formatted_hostname == "SometrackerTv"

def test_get_response_tracker_map():
    client = Client()
    trackers_map = ResponseTrackers(client).get_response_tracker_map()

    assert trackers