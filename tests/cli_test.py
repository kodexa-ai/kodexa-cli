from click.testing import CliRunner
from kodexa_cli.cli import configure  # replace this with the name of your module where configure command is defined
import os


def test_configure_command():
    runner = CliRunner()
    access_token = os.getenv("ACCESS_TOKEN")
    url = os.getenv("URL")
    profile = "test2"
    result = runner.invoke(configure,
                           input=f'{url}\n{access_token}\n{profile}\n')

    assert result.exit_code == 0
    assert 'Using default profile name' in result.output