import pickle
from lemon.system import NodePIDNotFound
import psutil
from pytest_mock.plugin import MockerFixture
from lemon.actions import (
    build,
    start,
    stop,
    show
)
from click.testing import CliRunner
from .utils import setup_client


def test_build_empty_mesh(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    mocker.patch('lemon.actions.open')
    mocker.patch('lemon.actions.yaml.safe_load', return_value=[{
        'mesh': 'mesh1',
        'nodes': []
    }])

    runner.invoke(build)
    client.set.assert_called_with('mesh1', pickle.dumps([]))


def test_build_with_node(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.build.init_health')
    runner = CliRunner()

    ossystem = mocker.patch('lemon.actions.os.system', return_value=0)
    node1 = {
        'name': 'node1',
        'node': 'node1',
        'from': 'source1'
    }

    mocker.patch('lemon.actions.open')
    mocker.patch('lemon.actions.yaml.safe_load', return_value=[{
        'mesh': 'mesh1',
        'nodes': [node1]
    }])

    runner.invoke(build)

    client.set.assert_any_call('mesh1', pickle.dumps([node1]))

    init_health.assert_called_once()
    assert str(ossystem.call_args[0][0]).endswith('pip install -e source1')


def test_build_with_node_name_only(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.build.init_health')
    runner = CliRunner()

    mocker.patch('lemon.actions.os.system', return_value=0)
    node1 = {
        'name': 'node1',
        'from': 'source1'
    }

    mocker.patch('lemon.actions.open')
    mocker.patch('lemon.actions.yaml.safe_load', return_value=[{
        'mesh': 'mesh1',
        'nodes': [node1]
    }])

    runner.invoke(build)

    client.set.assert_any_call('mesh1', pickle.dumps([node1]))

    init_health.assert_called_once()
    assert init_health.call_args[0][0].node == 'node1'


def test_build_with_invalid_yaml(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.build.init_health')
    runner = CliRunner()

    mocker.patch('lemon.actions.os.system', return_value=0)

    mocker.patch('lemon.actions.open')
    mocker.patch('lemon.actions.yaml.safe_load', return_value=[{
        # Purposeful omitted mandatory 'nodes'
        'mesh': 'mesh1'
    }])

    runner.invoke(build)

    client.set.assert_not_called()
    init_health.assert_not_called()


def test_build_with_failure(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.build.init_health')
    runner = CliRunner()

    system_call = mocker.patch('lemon.actions.os.system', return_value=1)

    mocker.patch('lemon.actions.open')
    node1 = {
        'name': 'node1',
        'from': 'source1'
    }
    mocker.patch('lemon.actions.yaml.safe_load', return_value=[{
        'mesh': 'mesh1',
        'nodes': [node1]
    }])

    runner.invoke(build)

    client.set.assert_not_called()
    init_health.assert_not_called()
    system_call.assert_called_once()


def test_start_node_process_started(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    process_start = mocker.patch('lemon.actions.ProcessService.start')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=False)
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])

    runner.invoke(start, ['mesh1'])

    assert process_start.call_count == 2


def test_start_with_exclusion(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    process_start = mocker.patch('lemon.actions.ProcessService.start')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=False)
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])

    runner.invoke(start, ['mesh1', '-x', 'node1'])

    process_start.assert_called_once()
    assert process_start.call_args[0][0].name == 'node2'


def test_start_with_select(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    process_start = mocker.patch('lemon.actions.ProcessService.start')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=False)
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])

    runner.invoke(start, ['mesh1', '-s', 'node1'])

    process_start.assert_called_once()
    assert process_start.call_args[0][0].name == 'node1'


def test_start_with_single_argument(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    process_start = mocker.patch('lemon.actions.ProcessService.start')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=False)
    client.get.return_value = pickle.dumps([{
        'name': 'node1',
        'node': 'node1',
        'with': '--test argument'
    }])

    runner.invoke(start, ['mesh1'])

    assert process_start.call_args[0][1] == ['--test argument']


def test_start_with_multiple_arguments(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    process_start = mocker.patch('lemon.actions.ProcessService.start')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=False)
    client.get.return_value = pickle.dumps([{
        'name': 'node1',
        'node': 'node1',
        'with': ['--test argument', '--test2 argument2']
    }])

    runner.invoke(start, ['mesh1'])

    assert process_start.call_args[0][1] == [
        '--test argument', '--test2 argument2']


def test_start_running_node_is_stopped_first(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    mocker.patch('lemon.actions.ProcessService.start')
    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    mocker.patch('lemon.actions.ProcessService.is_running', return_value=True)

    client.get.return_value = pickle.dumps([{
        'name': 'node1',
        'node': 'node1'
    }])

    runner.invoke(start, ['mesh1'])
    process_stop.assert_called_once()


def test_stop_node_shutdown(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.actions.init_health')
    runner = CliRunner()

    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    client.get.return_value = pickle.dumps([{
        'name': 'node1',
        'node': 'node1'
    }])
    runner.invoke(stop, ['mesh1'])

    init_health.assert_called_once()
    process_stop.assert_called_once()


def test_stop_node_not_found(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.actions.init_health')
    runner = CliRunner()

    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    client.get.return_value = pickle.dumps([{
        'name': 'node1',
        'node': 'node1'
    }])
    process_stop.side_effect = NodePIDNotFound()

    runner.invoke(stop, ['mesh1'])

    init_health.assert_not_called()
    process_stop.assert_called_once()


def test_stop_process_gone(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.actions.init_health')
    runner = CliRunner()

    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])
    process_stop.side_effect = psutil.NoSuchProcess(1)

    runner.invoke(stop, ['mesh1'])

    init_health.assert_not_called()
    assert process_stop.call_count == 2


def test_stop_with_select(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.actions.init_health')
    runner = CliRunner()

    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])
    process_stop.side_effect = psutil.NoSuchProcess(1)

    runner.invoke(stop, ['mesh1', '-s', 'node1'])

    init_health.assert_not_called()
    process_stop.assert_called_once()
    assert process_stop.call_args[0][0].name == 'node1'


def test_stop_with_exclusion(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    init_health = mocker.patch('lemon.actions.init_health')
    runner = CliRunner()

    process_stop = mocker.patch('lemon.actions.ProcessService.stop')
    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])
    process_stop.side_effect = psutil.NoSuchProcess(1)

    runner.invoke(stop, ['mesh1', '-x', 'node1'])

    init_health.assert_not_called()
    process_stop.assert_called_once()
    assert process_stop.call_args[0][0].name == 'node2'


def test_show(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    runner = CliRunner()

    client.get.return_value = pickle.dumps([
        {
            'name': 'node1',
            'node': 'node1'
        },
        {
            'name': 'node2',
            'node': 'node2'
        }
    ])

    get_health = mocker.patch('lemon.actions.get_health', return_value=(
        'inst', 'node', 'act', 'lftm', 'through'))

    runner.invoke(show, ['mesh1'])

    get_health.assert_called()
    assert len(get_health.call_args) == 2
    assert get_health.call_args_list[0][0][0].name == 'node1'
    assert get_health.call_args_list[1][0][0].name == 'node2'
