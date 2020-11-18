from typing import Protocol, Sequence, Mapping, Any


class CommandOutput(Protocol):
    """Protocol for command result."""

    def display(self):
        raise NotImplementedError


class Command(Protocol):
    """Protocol for commands."""

    def run(self) -> CommandOutput:
        raise NotImplementedError


class CommandError(Exception):
    def __init__(self, message):
        self.message = message


class CommandFactory(Protocol):
    def __call__(self, argv: Sequence[str], dependencies: Mapping[str, Any]) -> Command:
        raise NotImplementedError
