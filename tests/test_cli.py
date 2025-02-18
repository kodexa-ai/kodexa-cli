import pytest
from click.testing import CliRunner
from kodexa_cli.cli import cli, get_current_kodexa_profile

def test_verbose_option(cli_runner):
    """Test --verbose option sets logging level."""
    result = cli_runner.invoke(cli, ['--verbose', 'version'])
    assert result.exit_code == 0
    assert "Verbose logging is enabled" in result.output

def test_multiple_verbose_flags(cli_runner):
    """Test multiple --verbose flags increase logging level."""
    result = cli_runner.invoke(cli, ['-vv', 'version'])
    assert result.exit_code == 0
    assert "Verbose logging is enabled" in result.output
    assert "LEVEL=20" in result.output

def test_global_profile_option_valid(cli_runner, mock_kodexa_platform):
    """Test --profile option with valid profile."""
    result = cli_runner.invoke(cli, ['--profile', 'dev', 'version'])
    assert result.exit_code == 0
    mock_kodexa_platform.get_current_profile.assert_not_called()

def test_global_profile_option_invalid(cli_runner, mock_kodexa_platform):
    """Test --profile option with invalid profile."""
    result = cli_runner.invoke(cli, ['--profile', 'invalid', 'version'])
    assert result.exit_code == 1
    assert "Profile 'invalid' does not exist" in result.output
    assert "Available profiles: default,dev,prod" in result.output

def test_binary_help(tmp_path):
    """Test that the binary shows help text."""
    import subprocess
    import os
    
    binary_path = os.path.join(tmp_path, "kodexa")
    result = subprocess.run([binary_path, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_binary_version(tmp_path):
    """Test that the binary shows version."""
    import subprocess
    import os
    
    binary_path = os.path.join(tmp_path, "kodexa")
    result = subprocess.run([binary_path, "version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Kodexa Version:" in result.stdout
