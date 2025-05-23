import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

@pytest.fixture
def mock_config_check():
    """Mock config_check function to always return True."""
    with patch('kodexa_cli.cli.config_check', return_value=True) as mock:
        yield mock

@pytest.fixture
def mock_kodexa_platform():
    """Mock KodexaPlatform class methods."""
    with patch('kodexa_cli.cli.KodexaPlatform') as mock:
        # Setup default profile
        mock.list_profiles.return_value = ['default', 'dev', 'prod']
        mock.get_current_profile.return_value = 'default'
        mock.get_url.return_value = 'https://platform.kodexa.ai'
        mock.get_access_token.return_value = 'test-token'
        yield mock

@pytest.fixture
def cli_runner():
    """Create Click CLI runner."""
    return CliRunner()

@pytest.fixture
def mock_kodexa_client():
    """Mock KodexaClient class."""
    with patch('kodexa_cli.cli.KodexaClient') as mock:
        client = MagicMock()
        # Create a mock response object with empty content
        mock_response = MagicMock()
        mock_response.content = []
        client.list.return_value = mock_response
        mock.return_value = client
        yield client
