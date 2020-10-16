from typing import Protocol, TypeVar, Union, Sequence

from clutchless.external.transmission import TransmissionApi


class CommandResult(Protocol):
    """Protocol for command result."""

    def output(self):
        raise NotImplementedError


CR = TypeVar("CR", bound=CommandResult)


class CommandResultAccumulator(Protocol[CR]):
    """Since command results can have different fields, this handles adding to them polymorphically."""

    def accumulate(self, result: CR):
        raise NotImplementedError


class Command(Protocol):
    """Protocol for commands."""

    def run(self) -> CommandResult:
        raise NotImplementedError


class CommandFactoryWithoutClient(Protocol):
    def __call__(self, argv: Sequence[str]) -> Command:
        raise NotImplementedError


class CommandFactoryWithClient(Protocol):
    def __call__(self, argv: Sequence[str], client: TransmissionApi) -> Command:
        raise NotImplementedError


CommandFactory = Union[CommandFactoryWithClient, CommandFactoryWithoutClient]
