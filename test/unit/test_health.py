import pickle
from lemon.ctx import AsyncNodeContext, NodeContext
from lemon.health import HealthService, get_health, init_health
from lemon.utils import NodeActivity
import pytest
from pytest_mock import MockerFixture
from unittest.mock import MagicMock, AsyncMock


def setup_client(mocker: "MockerFixture", do_async=False) -> "MagicMock":
    client = AsyncMock() if do_async else MagicMock()
    return client, mocker.patch(
        'lemon.ctx.ensure_redis', return_value=client)


pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_update_active(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    ctx = AsyncNodeContext('mesh', 'name', 'node')

    srv = HealthService()
    await srv.update(ctx, NodeActivity.ACTIVE)

    assert client.set.call_args[0][0] == ('mesh:name:health')


def test_get_health_running(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext('mesh', 'name', 'node')

    mocker.patch(
        'lemon.health.ProcessService.is_running', return_value=True
    )

    mocker.patch(
        'lemon.health.time.time', return_value=22
    )

    data = (
        NodeActivity.ACTIVE,
        1,
        20
    )
    expected_data = (
        'name',
        'node',
        NodeActivity.ACTIVE,
        '00:00:21',
        '0.50 msg/s'
    )
    client.get.return_value = pickle.dumps(data)
    assert get_health(ctx) == expected_data


def test_get_health_should_run(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext('mesh', 'name', 'node')

    mocker.patch(
        'lemon.health.ProcessService.is_running', return_value=False
    )

    mocker.patch(
        'lemon.health.time.time', return_value=40
    )

    data = (
        NodeActivity.ACTIVE,
        1,
        20
    )
    expected_data = (
        'name',
        'node',
        NodeActivity.FAILED,
        '',
        ''
    )
    client.get.return_value = pickle.dumps(data)
    assert get_health(ctx) == expected_data


def test_get_health_isnt_running(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext('mesh', 'name', 'node')

    mocker.patch(
        'lemon.health.ProcessService.is_running', return_value=False
    )

    mocker.patch(
        'lemon.health.time.time', return_value=40
    )

    data = (
        NodeActivity.SHUTDOWN,
        1,
        20
    )
    expected_data = (
        'name',
        'node',
        NodeActivity.SHUTDOWN,
        '',
        ''
    )
    client.get.return_value = pickle.dumps(data)
    assert get_health(ctx) == expected_data


def test_get_health_waiting(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext('mesh', 'name', 'node')

    mocker.patch(
        'lemon.health.ProcessService.is_running', return_value=True
    )

    mocker.patch(
        'lemon.health.time.time', return_value=40
    )

    data = (
        NodeActivity.SHUTDOWN,
        1,
        20
    )
    expected_data = (
        'name',
        'node',
        NodeActivity.WAITING,
        '00:00:39',
        '0.05 msg/s'
    )
    client.get.return_value = pickle.dumps(data)
    assert get_health(ctx) == expected_data


def test_init_health(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext('mesh', 'name', 'node')
    init_health(ctx)
    client.set.assert_called_once()
