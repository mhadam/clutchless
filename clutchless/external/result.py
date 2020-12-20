from dataclasses import dataclass
from typing import Optional, TypeVar, Generic, Sequence


@dataclass
class CommandResult:
    error: Optional[str] = None
    id: Optional[int] = None
    success: bool = True


T = TypeVar("T")


@dataclass
class QueryResult(Generic[T]):
    value: Optional[T] = None
    error: Optional[str] = None
    success: bool = True


S = TypeVar("S")
F = TypeVar("F")


@dataclass
class Result(Generic[S, F]):
    success: Sequence[S]
    fail: Sequence[F]
