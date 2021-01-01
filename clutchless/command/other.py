from clutchless.command.command import CommandOutput, Command


class MissingCommandOutput(CommandOutput):
    def dry_run_display(self):
        raise NotImplementedError

    def display(self):
        print(
            "Empty command! This is probably a bug. Be ambitious, investigate it and fix it!"
        )


class MissingCommand(Command):
    def dry_run(self) -> CommandOutput:
        raise NotImplementedError

    def run(self) -> CommandOutput:
        return MissingCommandOutput()


class InvalidCommandOutput(CommandOutput):
    def dry_run_display(self):
        raise NotImplementedError

    def display(self):
        print("Invalid command!")


class InvalidCommand(Command):
    def dry_run(self) -> CommandOutput:
        raise NotImplementedError

    def run(self) -> CommandOutput:
        return InvalidCommandOutput()
