from collections import OrderedDict

from clutchless.service.torrent import AnnounceUrl, OrganizeService


def test_formatted_hostname():
    url = AnnounceUrl("http://domain.test.com/announce")

    assert url.formatted_hostname == "TestCom"


def test_split_hostname():
    result = AnnounceUrl.split_hostname("domain.test.com")

    assert result == ["test", "com"]


def test_split_hostname_smaller():
    result = AnnounceUrl.split_hostname("test.com")

    assert result == ["test", "com"]


def test_sort_url_sets():
    groups_by_name = {
        "AnotherNet": {
            "http://domain.another.net/announce",
            "http://domain.another.net/announce2",
        },
        "TestCom": {"http://domain.test.com/announce"},
    }
    result = OrganizeService._sort_url_sets(groups_by_name)

    assert result == {
        "AnotherNet": [
            "http://domain.another.net/announce",
            "http://domain.another.net/announce2",
        ],
        "TestCom": ["http://domain.test.com/announce"],
    }


def test_sort_groups_by_name():
    groups = {
        "TestCom": {"http://domain.test.com/announce"},
        "AnotherNet": {
            "http://domain.another.net/announce",
            "http://domain.another.net/announce2",
        },
    }
    result = OrganizeService._sort_groups_by_name(groups)

    assert result == {
        "AnotherNet": {
            "http://domain.another.net/announce",
            "http://domain.another.net/announce2",
        },
        "TestCom": {"http://domain.test.com/announce"},
    }


def test_get_groups_by_name():
    announce_urls = {
        "http://domain.test.com/announce",
        "http://domain.another.net/announce",
        "http://domain.another.net/announce2",
    }
    result = OrganizeService._get_groups_by_name(announce_urls)

    assert result == {
        "AnotherNet": {
            "http://domain.another.net/announce",
            "http://domain.another.net/announce2",
        },
        "TestCom": {"http://domain.test.com/announce"},
    }
