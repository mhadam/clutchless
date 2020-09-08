from pathlib import Path

from pytest import raises

from clutchless.parse.shared import TorrentFileCrawler, DataDirectoryParser, PathParser


def test_path_parser_existing(tmpdir):
    first_dir = tmpdir.join("test")
    first_dir.mkdir()
    second_dir = tmpdir.join("test2")
    second_dir.mkdir()
    raw_paths = [test_dir.strpath for test_dir in [first_dir, second_dir]]

    paths = PathParser.parse_paths(raw_paths)

    assert paths == {Path(raw_path) for raw_path in raw_paths}


def test_path_parser_nonexistent(tmpdir):
    raw_paths = ['/fake_dir']

    with raises(FileNotFoundError) as e:
        _ = PathParser.parse_paths(raw_paths)

    assert e.value.errno == 2


def test_crawl(tmpdir):
    first_dir = tmpdir.join("test")
    first_dir.mkdir()
    empty_dir = tmpdir.join("test2")
    empty_dir.mkdir()

    nested_file = first_dir.join("file.torrent")
    nested_file.write('testing')

    second_file = tmpdir.join("file2.torrent")
    second_file.write('testing')

    cases = [first_dir, second_file, empty_dir]
    raw_paths = [case.strpath for case in cases]
    paths = PathParser.parse_paths(raw_paths)

    crawler = TorrentFileCrawler()
    result = crawler.crawl(paths)

    expected_result = {
        Path(path.strpath) for path in [nested_file, second_file]
    }

    assert result == expected_result


def test_crawl_with_nonexistent_path(tmpdir):
    nonexistent_dir = tmpdir.join("test2")
    paths = [Path(nonexistent_dir.strpath)]

    with raises(ValueError) as e:
        crawler = TorrentFileCrawler()
        crawler.crawl(paths)

    assert "supplied torrent path doesn't exist" in str(e.value).lower()


def test_parse_data_dirs(tmpdir):
    data_dir = tmpdir.join("test_directory")
    data_dir.mkdir()

    parser = DataDirectoryParser()
    result = parser.parse([data_dir.strpath])

    assert result == {
        Path(data_dir.strpath)
    }


def test_parse_data_dirs_nonexistent(tmpdir):
    data_dir = tmpdir.join("test_directory")

    with raises(ValueError) as e:
        parser = DataDirectoryParser()
        _ = parser.parse([data_dir.strpath])

    assert "supplied data path doesn't exist" in str(e.value).lower()


def test_parse_data_dirs_file(tmpdir):
    test_file = tmpdir.join("file.txt")
    test_file.write('testing')

    with raises(ValueError) as e:
        parser = DataDirectoryParser()
        _ = parser.parse([test_file.strpath])

    assert "supplied data path isn't a directory" in str(e.value).lower()
