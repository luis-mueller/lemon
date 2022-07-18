from unittest.mock import AsyncMock, MagicMock
from lemon.ctx import AsyncNodeContext, NodeContext
from lemon.system import ProcessService
import pytest
from pytest_mock import MockerFixture


def setup_client(mocker: "MockerFixture", do_async=False) -> "MagicMock":
    client = AsyncMock() if do_async else MagicMock()
    return client, mocker.patch(
        'lemon.ctx.ensure_redis', return_value=client)


pytest_plugins = ('pytest_asyncio',)


@pytest.mark.asyncio
async def test_self_register(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch(
        'lemon.system.os.getpid', return_value=1000
    )

    await ProcessService.self_register(ctx)

    client.set.assert_called_once_with('mesh:name:pid', 1000)


def test_stop_ctrl_c_works(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    client.get.return_value = b'1000'

    ctx = NodeContext('mesh', 'name', 'node')

    process = mocker.patch(
        'lemon.system.psutil.Process'
    )
    process.is_running.return_value = False

    ProcessService.stop(ctx)
    process.terminate.assert_not_called()


def test_stop_ctr_c_doesnt_work(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    client.get.return_value = b'1000'

    ctx = NodeContext('mesh', 'name', 'node')
    mocker.patch(
        'lemon.system.os.getpid', return_value=1000
    )
    process = MagicMock()
    mocker.patch(
        'lemon.system.psutil.Process', return_value=process
    )
    process.is_running.return_value = True

    ProcessService.stop(ctx)
    process.terminate.assert_called_once()


def test_is_running_pid_in_redis_but_not_system(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    client.get.return_value = b'1000'

    ctx = NodeContext('mesh', 'name', 'node')
    mocker.patch(
        'lemon.system.os.getpid', return_value=1000
    )
    mocker.patch(
        'lemon.system.psutil.pid_exists', return_value=False
    )

    assert not ProcessService.is_running(ctx)


def test_is_running_pid_in_redis_and_in_system(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    client.get.return_value = b'1000'

    ctx = NodeContext('mesh', 'name', 'node')
    mocker.patch(
        'lemon.system.os.getpid', return_value=1000
    )
    mocker.patch(
        'lemon.system.psutil.pid_exists', return_value=True
    )

    assert ProcessService.is_running(ctx)


def test_is_running_pid_not_in_system(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)
    client.get.return_value = None

    ctx = NodeContext('mesh', 'name', 'node')
    mocker.patch(
        'lemon.system.os.getpid', return_value=1000
    )
    exists = mocker.patch(
        'lemon.system.psutil.pid_exists'
    )

    assert not ProcessService.is_running(ctx)
    exists.assert_not_called()
