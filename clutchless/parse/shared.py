import os
from pathlib import Path
from typing import Set, Sequence


class TorrentFileCrawler:
    def __init__(self):
        pass

    def crawl(self, raw_paths: Sequence[str]) -> Set[Path]:
        paths = self.__convert_to_paths(raw_paths)
        return self.__find_torrent_files(paths)

    def __convert_to_paths(self, raw_paths: Sequence[str]) -> Set[Path]:
        return {Path(raw_path).resolve(strict=False) for raw_path in raw_paths}

    def __find_torrent_files(self, paths: Set[Path]) -> Set[Path]:
        torrent_dirs = set()
        torrent_files = set()
        for path in paths:
            self.__handle_path(path, torrent_dirs, torrent_files)
        return self.__collect_files(torrent_dirs, torrent_files)

    def __validate_path_exists(self, path: Path):
        if not path.exists():
            raise ValueError("Supplied torrent path doesn't exist")

    def __handle_path(
        self, path: Path, torrent_dirs: Set[Path], torrent_files: Set[Path]
    ):
        self.__validate_path_exists(path)
        torrent_dirs.update(self.__get_torrent_dir(path))
        torrent_files.update(self.__get_torrent_file(path))

    def __get_torrent_file(self, path: Path) -> Set[Path]:
        if path.is_file():
            return {path}
        return set()

    def __get_torrent_dir(self, path: Path) -> Set[Path]:
        if path.is_dir():
            return {path}
        return set()

    def __collect_files(
        self, torrent_dirs: Set[Path], torrent_files: Set[Path]
    ) -> Set[Path]:
        for directory in torrent_dirs:
            torrent_files.update(self.__get_torrent_files(directory))
        return torrent_files

    def __get_torrent_files(self, torrent_dir: Path) -> Set[Path]:
        result: Set[Path] = set()
        for root, directories, files in os.walk(torrent_dir.resolve(strict=True)):
            for file in files:
                file_path = Path(root, file)
                if file_path.suffix == ".torrent":
                    result.add(file_path)
        return result


class DataDirectoryParser:
    def __init__(self):
        pass

    def parse(self, data_dirs: Sequence[str]) -> Set[Path]:
        paths = [Path(data_dir) for data_dir in data_dirs]
        result = set()
        for path in paths:
            result.update(self.__handle_path(path))
        return result

    def __handle_path(self, path: Path) -> Set[Path]:
        self.__validate_exists(path)
        self.__reject_non_dir(path)
        return self.__handle_dir(path)

    def __validate_exists(self, path: Path):
        if not path.exists():
            raise ValueError("Supplied data path doesn't exist")

    def __reject_non_dir(self, path: Path):
        if not path.is_dir():
            raise ValueError("Supplied data path isn't a directory")

    def __handle_dir(self, path: Path) -> Set[Path]:
        if path.is_dir():
            return {path}
        return set()
