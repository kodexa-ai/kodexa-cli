import pytest
from kodexa_cli.cli import cli, profile, get_current_kodexa_profile, get_current_kodexa_url, get_current_access_token

def test_profile_list(cli_runner, mock_kodexa_platform):
    """Test profile --list command."""
    result = cli_runner.invoke(cli, ['profile', '--list'])
    assert result.exit_code == 0
    assert 'default' in result.output
    assert 'dev' in result.output
    assert 'prod' in result.output

def test_profile_set_valid(cli_runner, mock_kodexa_platform):
    """Test setting valid profile."""
    result = cli_runner.invoke(cli, ['profile', 'dev'])
    assert result.exit_code == 0
    mock_kodexa_platform.set_profile.assert_called_once_with('dev')

def test_profile_set_invalid(cli_runner, mock_kodexa_platform):
    """Test setting invalid profile."""
    result = cli_runner.invoke(cli, ['profile', 'invalid'])
    assert result.exit_code == 1
    assert "Profile 'invalid' does not exist" in result.output
    mock_kodexa_platform.set_profile.assert_not_called()

def test_profile_delete_valid(cli_runner, mock_kodexa_platform):
    """Test deleting valid profile."""
    result = cli_runner.invoke(cli, ['profile', 'dev', '--delete'])
    assert result.exit_code == 0
    mock_kodexa_platform.delete_profile.assert_called_once_with('dev')

def test_profile_delete_invalid(cli_runner, mock_kodexa_platform):
    """Test deleting invalid profile."""
    result = cli_runner.invoke(cli, ['profile', 'invalid', '--delete'])
    assert result.exit_code == 1
    assert "Profile 'invalid' does not exist" in result.output
    mock_kodexa_platform.delete_profile.assert_not_called()

def test_get_current_kodexa_profile(mock_kodexa_platform):
    """Test get_current_kodexa_profile function."""
    mock_kodexa_platform.get_current_profile.return_value = 'test'
    assert get_current_kodexa_profile() == 'test'

def test_get_current_kodexa_url(mock_kodexa_platform):
    """Test get_current_kodexa_url function."""
    mock_kodexa_platform.get_url.return_value = 'https://test.kodexa.ai'
    assert get_current_kodexa_url() == 'https://test.kodexa.ai'

def test_get_current_access_token(mock_kodexa_platform):
    """Test get_current_access_token function."""
    mock_kodexa_platform.get_access_token.return_value = 'test-token'
    assert get_current_access_token() == 'test-token'


def test_profiles_command(cli_runner, mock_kodexa_platform):
    """Test profiles command."""
    mock_kodexa_platform.list_profiles.return_value = ['default', 'dev']
    mock_kodexa_platform.get_url.side_effect = lambda p: f'https://{p}.kodexa.ai'
    
    result = cli_runner.invoke(cli, ['profiles'])
    assert result.exit_code == 0
    assert 'default: https://default.kodexa.ai' in result.output
    assert 'dev: https://dev.kodexa.ai' in result.output


def test_profiles_command_error(cli_runner, mock_kodexa_platform):
    """Test profiles command with error."""
    mock_kodexa_platform.list_profiles.side_effect = Exception("Test error")
    
    result = cli_runner.invoke(cli, ['profiles'])
    assert result.exit_code == 1
    assert "Profile Error" in result.output
    assert "Could not list profiles" in result.output
    assert "Test error" in result.output