import pytest
from kodexa_cli.cli import cli

def test_upload_file(cli_runner, mock_kodexa_client, mock_config_check):
    """Test uploading a file."""
    result = cli_runner.invoke(cli, [
        'upload',
        'store/test',
        'test.txt'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_object_by_ref.assert_called_once_with('store', 'store/test')

def test_upload_file_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform, mock_config_check):
    """Test uploading a file with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'upload',
        'store/test',
        'test.txt'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_object_by_ref.assert_called_once_with('store', 'store/test')

