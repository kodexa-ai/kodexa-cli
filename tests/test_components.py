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

def test_dataclasses(cli_runner, mock_kodexa_client):
    """Test listing dataclasses."""
    result = cli_runner.invoke(cli, ['dataclasses'])
    assert result.exit_code == 0
    mock_kodexa_client.get_dataclasses.assert_called_once()

def test_version(cli_runner):
    """Test version command."""
    result = cli_runner.invoke(cli, ['version'])
    assert result.exit_code == 0
    assert result.output.strip() != ""

def test_package(cli_runner, mock_kodexa_client):
    """Test packaging a component."""
    result = cli_runner.invoke(cli, ['package', 'test-component'])
    assert result.exit_code == 0
    mock_kodexa_client.package_component.assert_called_once()

def test_package_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform):
    """Test packaging a component with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'package',
        'test-component'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.package_component.assert_called_once()
