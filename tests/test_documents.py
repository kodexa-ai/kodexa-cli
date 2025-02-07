import pytest
from kodexa_cli.cli import cli

def test_upload_file(cli_runner, mock_kodexa_client):
    """Test uploading a file."""
    result = cli_runner.invoke(cli, [
        'upload',
        'store/test',
        'test.txt'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_object_by_ref.assert_called_once_with('store', 'store/test')

def test_upload_file_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform):
    """Test uploading a file with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'upload',
        'store/test',
        'test.txt'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_object_by_ref.assert_called_once_with('store', 'store/test')

def test_download_implementation(cli_runner, mock_kodexa_client):
    """Test downloading implementation."""
    result = cli_runner.invoke(cli, [
        'download-implementation',
        'test-implementation'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.get_implementation.assert_called_once_with('test-implementation')

def test_get_objects(cli_runner, mock_kodexa_client):
    """Test getting objects."""
    result = cli_runner.invoke(cli, ['get', 'stores'])
    assert result.exit_code == 0
    mock_kodexa_client.get_objects.assert_called_once()

def test_get_object_by_ref(cli_runner, mock_kodexa_client):
    """Test getting object by reference."""
    result = cli_runner.invoke(cli, ['get', 'store/test'])
    assert result.exit_code == 0
    mock_kodexa_client.get_object_by_ref.assert_called_once_with('store', 'test')

def test_query_simple(cli_runner, mock_kodexa_client):
    """Test simple query."""
    result = cli_runner.invoke(cli, ['query', 'test-query'])
    assert result.exit_code == 0
    mock_kodexa_client.query.assert_called_once()

def test_query_with_family(cli_runner, mock_kodexa_client):
    """Test query with family parameter."""
    result = cli_runner.invoke(cli, ['query', 'test-query', '--family', 'test-family'])
    assert result.exit_code == 0
    mock_kodexa_client.query.assert_called_once()

def test_query_with_profile(cli_runner, mock_kodexa_client, mock_kodexa_platform):
    """Test query with profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'query',
        'test-query'
    ])
    assert result.exit_code == 0
    mock_kodexa_client.query.assert_called_once()
