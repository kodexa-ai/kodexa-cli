import pytest
from kodexa_cli.cli import cli

def test_logs(cli_runner, mock_kodexa_client):
    """Test viewing logs."""
    result = cli_runner.invoke(cli, ['logs', 'test-component'])
    assert result.exit_code == 0

def test_delete_component(cli_runner, mock_kodexa_client):
    """Test deleting a component."""
    result = cli_runner.invoke(cli, ['delete', 'test-component'])
    assert result.exit_code == 0
    mock_kodexa_client.delete_component.assert_called_once()

def test_version(cli_runner):
    """Test version command."""
    result = cli_runner.invoke(cli, ['version'])
    assert result.exit_code == 0
    assert result.output.strip() != ""
