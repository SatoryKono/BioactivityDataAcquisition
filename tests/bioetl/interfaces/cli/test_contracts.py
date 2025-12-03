from bioetl.interfaces.cli.contracts import CLICommandABC


def test_cli_command_abc():
    class TestCommand(CLICommandABC):
        def register(self, app):
            pass

        def run_pipeline(self, config, options):
            return "result"

    cmd = TestCommand()
    assert isinstance(cmd, CLICommandABC)
    assert cmd.run_pipeline(None, {}) == "result"
