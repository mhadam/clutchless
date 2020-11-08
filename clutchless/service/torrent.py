from pathlib import Path
from typing import Iterable, Set, MutableSequence, Mapping

from clutchless.domain.torrent import MetainfoFile, LinkedMetainfo
from clutchless.external.filesystem import Filesystem
from clutchless.external.transmission import TransmissionApi


class AddService:
    def __init__(self, api: TransmissionApi):
        self.api = api
        self.success: MutableSequence[Path] = []
        self.added_without_data: MutableSequence[Path] = []
        # these are added together (if linking)
        # found -> metainfo file path
        self.found: MutableSequence[Path] = []
        # link -> data location path
        self.link: MutableSequence[Path] = []

        # these are added together
        self.fail: MutableSequence[Path] = []
        self.error: MutableSequence[str] = []

    def add(self, path: Path):
        result = self.api.add_torrent(path)
        if result.success:
            self.success.append(path)
            self.added_without_data.append(path)
        else:
            self.fail.append(path)
            self.error.append(result.error)

    def add_with_data(self, metainfo_path: Path, data_path: Path):
        result = self.api.add_torrent_with_files(metainfo_path, data_path)
        if result.success:
            self.success.append(metainfo_path)
            self.found.append(metainfo_path)
            self.link.append(data_path)
        else:
            self.fail.append(metainfo_path)
            self.error.append(result.error)


class LinkService:
    def __init__(self, fs: Filesystem, search_dirs: Set[Path]):
        self.fs = fs
        self.search_dirs = search_dirs

    def __search_dirs(self, file: MetainfoFile) -> Iterable[LinkedMetainfo]:
        for search_dir in self.search_dirs:
            linked = file.link(self.fs, search_dir)
            if linked:
                return [linked]
        return []

    def find(self, metainfo_files: Set[MetainfoFile]) -> Set[LinkedMetainfo]:
        def generate() -> Iterable[LinkedMetainfo]:
            for file in metainfo_files:
                yield from self.__search_dirs(file)

        return set(generate())
