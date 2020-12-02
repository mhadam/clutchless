from pathlib import Path
from typing import Set, Sequence


class PathParser:
    def __init__(self):
        pass

    @classmethod
    def parse_paths(cls, raw_paths: Sequence[str]) -> Set[Path]:
        return {cls.parse_path(raw_path) for raw_path in raw_paths}

    @classmethod
    def parse_path(cls, raw_path: str) -> Path:
        return Path(raw_path).resolve(strict=True)
