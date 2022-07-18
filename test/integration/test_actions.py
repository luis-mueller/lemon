import os
from click.testing import CliRunner
from lemon.actions import create
import shutil


def test_create_basic_structure():
    runner = CliRunner()
    runner.invoke(create, ['my-node'])

    assert os.path.exists('my-node')
    assert os.path.exists('my-node/setup.py')
    assert os.path.exists('my-node/my_node.py')
    assert os.path.exists('my-node/my_node.cpp')

    shutil.rmtree('my-node')
