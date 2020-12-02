from typing import Protocol, Sequence, Mapping, Any, Tuple


class CommandOutput(Protocol):
    """Protocol for command result."""

    def dry_run_display(self):
        raise NotImplementedError

    def display(self):
        raise NotImplementedError


class Command(Protocol):
    """Protocol for commands."""

    def dry_run(self) -> CommandOutput:
        raise NotImplementedError

    def run(self) -> CommandOutput:
        raise NotImplementedError


class CommandError(Exception):
    def __init__(self, message):
        self.message = message


CommandFactoryResult = Tuple[Command, Mapping]


class CommandFactory(Protocol):
    def __call__(
        self, argv: Sequence[str], dependencies: Mapping[str, Any]
    ) -> CommandFactoryResult:
        raise NotImplementedError
