from typing import Protocol, TypeVar, Union, Sequence

from clutchless.external.transmission import TransmissionApi


class CommandOutput(Protocol):
    """Protocol for command result."""

    def display(self):
        raise NotImplementedError


CO = TypeVar("CO", bound=CommandOutput)


class CommandOutputAccumulator(Protocol[CO]):
    """Since command results can have different fields, this handles adding to them polymorphically."""

    def accumulate(self, result: CO):
        raise NotImplementedError


class Command(Protocol):
    """Protocol for commands."""

    def run(self) -> CommandOutput:
        raise NotImplementedError


class CommandError(Exception):
    def __init__(self, message):
        self.message = message


class CommandFactoryWithoutClient(Protocol):
    def __call__(self, argv: Sequence[str]) -> Command:
        raise NotImplementedError


class CommandFactoryWithClient(Protocol):
    def __call__(self, argv: Sequence[str], client: TransmissionApi) -> Command:
        raise NotImplementedError


CommandFactory = Union[CommandFactoryWithClient, CommandFactoryWithoutClient]
