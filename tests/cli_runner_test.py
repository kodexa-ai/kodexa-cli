from click.testing import CliRunner
from kodexa_cli.cli import get  # replace this with the name of your module where configure command is defined
import os


def test_configure_command():
    runner = CliRunner()
    result = runner.invoke(get, ["org"])