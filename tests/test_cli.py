import json

import pytest

from cli import get, deploy
from click.testing import CliRunner

URL = 'https://model-training.kodexa.com'
TOKEN = 'db89ce531dfb414a85d63d58d8f5ed6b'
ORG = 'regression-test'
UPDATE = True
FILE = '../taxonomy.yml'


class TestCLI():
    def __init__(self):
        self.url = None
        self.token = None
        self.org = None
        self.update = False
        self.file = None
        self.ref = None

    def dev_env_settings(self):
        self.url = 'https://dev1.kodexa.com'
        self.token = '60ad7b600f0a4565a8ee49330c8ce1a6'
        self.org = 'regression-test'
        self.update = True

    def regression_env_settings(self):
        self.url = 'https://model-training.kodexa.com'
        self.token = '4a3050ae339649fcb737de6a10cbab2d'
        self.ref = 'regression-test'
        self.update = True


test_class_cli = TestCLI()
get_process_command_list = [f'taxon {test_class_cli.org}/utilities-invoicing-taxonomy',
                            'dataForm regression-test/dataForm',
                            'taxon regression-test/project-template']


@pytest.mark.parametrize('object_type', ['stores'])
def test_get(object_type):
    test_class_cli = TestCLI()
    test_class_cli.regression_env_settings()
    runner = CliRunner()

    # Append url and token
    cli_command = object_type + f' {test_class_cli.ref} --url {test_class_cli.url} --token {test_class_cli.token}'
    results = runner.invoke(get, cli_command)
    if results.exception:
        print(results.exception)
        assert False
    else:
        assert True


def test_deploy():
    test_class_cli = TestCLI()
    runner = CliRunner()
    test_class_cli.dev_env_settings()
    results = \
        runner.invoke(deploy, f'--file {test_class_cli.file} --url {test_class_cli.url} '
                              f'--org {test_class_cli.org} --token {test_class_cli.token} --update')
    if results.exception:
        print(results.exception)
        assert False
    else:
        assert True
