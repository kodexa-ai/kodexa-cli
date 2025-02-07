import pytest
from kodexa_cli.cli import cli

def test_login_with_args(cli_runner, mock_kodexa_platform):
    """Test login with command line arguments."""
    result = cli_runner.invoke(cli, [
        'login',
        '--url', 'https://test.kodexa.ai',
        '--token', 'test-token'
    ])
    assert result.exit_code == 0
    mock_kodexa_platform.login.assert_called_once_with(
        'https://test.kodexa.ai',
        'test-token',
        'default'
    )

def test_login_with_profile_override(cli_runner, mock_kodexa_platform):
    """Test login with global --profile override."""
    result = cli_runner.invoke(cli, [
        '--profile', 'dev',
        'login',
        '--url', 'https://test.kodexa.ai',
        '--token', 'test-token'
    ])
    assert result.exit_code == 0
    mock_kodexa_platform.login.assert_called_once_with(
        'https://test.kodexa.ai',
        'test-token',
        'dev'
    )

def test_login_interactive(cli_runner, mock_kodexa_platform):
    """Test login with interactive input."""
    inputs = [
        'https://test.kodexa.ai',  # URL
        'test-token',              # Token
        'test-profile'             # Profile name
    ]
    result = cli_runner.invoke(cli, ['login'], input='\n'.join(inputs))
    assert result.exit_code == 0
    mock_kodexa_platform.login.assert_called_once_with(
        'https://test.kodexa.ai',
        'test-token',
        'test-profile'
    )

def test_login_default_url(cli_runner, mock_kodexa_platform):
    """Test login with empty URL defaults to platform.kodexa.ai."""
    inputs = [
        '',                # Empty URL (should default)
        'test-token',     # Token
        'test-profile'    # Profile name
    ]
    result = cli_runner.invoke(cli, ['login'], input='\n'.join(inputs))
    assert result.exit_code == 0
    mock_kodexa_platform.login.assert_called_once_with(
        'https://platform.kodexa.ai',
        'test-token',
        'test-profile'
    )
