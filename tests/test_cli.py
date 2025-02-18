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

@pytest.fixture(scope="session")
def binary_path(tmp_path_factory):
    """Build the binary once for all tests."""
    import subprocess
    import os
    import shutil

    # Create a temporary directory for the binary
    binary_dir = tmp_path_factory.mktemp("binary")
    binary_path = os.path.join(binary_dir, "kodexa")

    # Build the binary first
    result = subprocess.run(["poetry", "run", "pyinstaller", "kodexa-cli.spec"], 
                          capture_output=True, text=True)
    if result.returncode != 0:
        print("PyInstaller output:")
        print(result.stdout)
        print(result.stderr)
        result.check_returncode()
    
    # Copy the binary to our test directory
    shutil.copy("dist/kodexa", binary_path)
    
    # Make it executable
    os.chmod(binary_path, 0o755)
    
    return binary_path

def test_binary_help(binary_path):
    """Test that the binary shows help text."""
    import subprocess
    
    result = subprocess.run([binary_path, "--help"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Usage:" in result.stdout

def test_binary_version(binary_path):
    """Test that the binary shows version."""
    import subprocess
    
    result = subprocess.run([binary_path, "version"], capture_output=True, text=True)
    assert result.returncode == 0
    assert "Kodexa Version:" in result.stdout
