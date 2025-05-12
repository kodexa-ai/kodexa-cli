import pytest
from kodexa_cli.cli import cli

def test_export_project(cli_runner, mock_kodexa_client, mock_config_check):
    """Test exporting a project."""
    result = cli_runner.invoke(cli, ['export-project', 'test-project'])
    assert result.exit_code == 0
    mock_kodexa_client.get_project.assert_called_once_with('test-project')

def test_export_project_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform, mock_config_check):
    """Test exporting a project with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'export-project',
        'test-project'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_project.assert_called_once_with('test-project')

def test_import_project(cli_runner, mock_kodexa_client, mock_config_check):
    """Test importing a project."""
    result = cli_runner.invoke(cli, ['import-project', 'test-project.json'])
    assert result.exit_code == 0
    mock_kodexa_client.import_project.assert_called_once()

def test_bootstrap(cli_runner, mock_kodexa_client, mock_config_check):
    """Test bootstrapping a project."""
    result = cli_runner.invoke(cli, ['bootstrap', 'test-project'])
    assert result.exit_code == 0
    mock_kodexa_client.create_project.assert_called_once()

def test_bootstrap_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform, mock_config_check):
    """Test bootstrapping a project with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'bootstrap',
        'test-project'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.create_project.assert_called_once()

def test_send_event(cli_runner, mock_kodexa_client, mock_config_check):
    """Test sending an event."""
    result = cli_runner.invoke(cli, [
        'send-event',
        'test-event',
        '--type', 'test-type',
        '--data', '{"key": "value"}'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.send_event.assert_called_once()

def test_send_event_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform, mock_config_check):
    """Test sending an event with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'send-event',
        'test-event',
        '--type', 'test-type',
        '--data', '{"key": "value"}'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.send_event.assert_called_once()
