import asyncio
import pickle
from unittest.mock import AsyncMock, MagicMock
from lemon.api import (
    anyone_listening,
    entrypoint,
    get_ctx,
    parameter,
    subscribe,
    publish
)
from lemon.ctx import AsyncNodeContext
from lemon.utils import NodeActivity
import pytest
from pytest_mock import MockerFixture
from click.testing import CliRunner
import redis


def setup_client(mocker: "MockerFixture", do_async=False) -> "MagicMock":
    client = AsyncMock() if do_async else MagicMock()
    return client, mocker.patch(
        'lemon.ctx.ensure_redis', return_value=client)


pytest_plugins = ('pytest_asyncio',)


def test_entrypoint_only_mesh_provided(mocker: "MockerFixture"):
    ctx = MagicMock()
    ctx_init = mocker.patch(
        'lemon.api.AsyncNodeContext', return_value=ctx)

    health = MagicMock()
    health.update = AsyncMock()
    mocker.patch(
        'lemon.api.HealthService', return_value=health)

    self_register = mocker.patch(
        'lemon.api.ProcessService.self_register')

    mocker.patch(
        'lemon.api.sys.argv',
        ['path/to/node/node-name'])

    fn = AsyncMock()
    wrapped_fn = entrypoint(fn)

    runner = CliRunner()
    runner.invoke(wrapped_fn, ['mesh'])

    ctx_init.assert_called_once_with(
        'mesh', 'node-name', 'node-name')
    self_register.assert_called_once_with(ctx)
    fn.assert_called_once_with()
    health.update.assert_called_once_with(ctx, NodeActivity.SHUTDOWN)
    ctx.redis_client.close.assert_called_once()


def test_entrypoint_mesh_and_name_provided(mocker: "MockerFixture"):
    ctx = MagicMock()
    ctx_init = mocker.patch(
        'lemon.api.AsyncNodeContext', return_value=ctx)

    health = MagicMock()
    health.update = AsyncMock()
    mocker.patch(
        'lemon.api.HealthService', return_value=health)

    self_register = mocker.patch(
        'lemon.api.ProcessService.self_register')

    mocker.patch(
        'lemon.api.sys.argv',
        ['path/to/node/node-name'])

    fn = AsyncMock()
    wrapped_fn = entrypoint(fn)

    runner = CliRunner()
    runner.invoke(wrapped_fn, ['mesh', '-n', 'other-node-name'])

    ctx_init.assert_called_once_with(
        'mesh', 'other-node-name', 'node-name')
    self_register.assert_called_once_with(ctx)
    fn.assert_called_once_with()
    health.update.assert_called_once_with(ctx, NodeActivity.SHUTDOWN)
    ctx.redis_client.close.assert_called_once()


def test_entrypoint_ctrl_c(mocker: "MockerFixture"):
    ctx = MagicMock()
    mocker.patch(
        'lemon.api.AsyncNodeContext', return_value=ctx)

    health = MagicMock()
    health.update = AsyncMock()
    mocker.patch(
        'lemon.api.HealthService', return_value=health)

    mocker.patch(
        'lemon.api.ProcessService.self_register')

    mocker.patch(
        'lemon.api.sys.argv',
        ['path/to/node/node-name'])

    fn = AsyncMock(side_effect=KeyboardInterrupt())
    wrapped_fn = entrypoint(fn)

    runner = CliRunner()
    runner.invoke(wrapped_fn, ['mesh'])

    health.update.assert_called_once_with(ctx, NodeActivity.SHUTDOWN)
    ctx.redis_client.close.assert_called_once()


@pytest.mark.asyncio
async def test_subscribe_to_complete_topic(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.get_message = AsyncMock(return_value={
        'channel': b'my_topic',
        'data': pickle.dumps(5562)
    })
    client.pubsub = MagicMock(return_value=pubsub)

    health = AsyncMock()
    mocker.patch(
        'lemon.api.API.health_service', health)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)

    callback = AsyncMock()

    try:
        await asyncio.wait_for(subscribe({'my_topic': callback}), timeout=1e-1)
    except asyncio.TimeoutError:
        pass

    pubsub.subscribe.assert_called_once_with('my_topic')
    callback.assert_called_with(5562)
    health.update.assert_called_with(ctx, NodeActivity.ACTIVE)


@pytest.mark.asyncio
async def test_subscribe_ConnectionError_downscale(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.get_message = AsyncMock(
        side_effect=redis.exceptions.ConnectionError())
    client.pubsub = MagicMock(return_value=pubsub)

    health = AsyncMock()
    mocker.patch(
        'lemon.api.API.health_service', health)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    ctx.renew = MagicMock()
    mocker.patch('lemon.api.API.ctx', ctx)

    callback = AsyncMock()

    try:
        await asyncio.wait_for(subscribe({'my_topic': callback}), timeout=1e-1)
    except asyncio.TimeoutError:
        pass

    ctx.renew.assert_called()


@pytest.mark.asyncio
async def test_publish_to_complete_topic(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    health = AsyncMock()
    mocker.patch(
        'lemon.api.API.health_service', health)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)

    await publish('my_topic', [[.5]])

    expected_topic = 'my_topic'

    health.update.assert_called_once_with(ctx, NodeActivity.ACTIVE)
    client.publish.assert_called_once_with(
        expected_topic, pickle.dumps([[.5]]))


@pytest.mark.asyncio
async def test_parameter_shared_false(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)

    value = .5

    callback = AsyncMock()
    rt = await parameter('my_param', value, fn=callback, shared=False)

    expected_topic = '!param:mesh:name:my_param'
    assert rt == {'!param:mesh:name:my_param': callback}

    client.set.assert_called_once_with(
        expected_topic, pickle.dumps(value))


@pytest.mark.asyncio
async def test_parameter_shared_true(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)

    value = .5

    callback = AsyncMock()
    rt = await parameter('my_param', value, fn=callback, shared=True)

    expected_topic = '!param:mesh:my_param'
    assert rt == {'!param:mesh:my_param': callback}

    client.set.assert_called_once_with(
        expected_topic, pickle.dumps(value))


@pytest.mark.asyncio
async def test_parameter_gets_initialized(mocker: "MockerFixture"):
    setup_client(mocker, do_async=True)

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)

    value = .5

    callback = AsyncMock()
    await parameter('my_param', value, fn=callback, shared=True)

    callback.assert_called_once_with(value)


@pytest.mark.asyncio
async def test_anyone_listening(mocker: "MockerFixture"):
    client, _ = setup_client(mocker, do_async=True)
    client.pubsub_numsub = AsyncMock(
        return_value=[(b'hello', 2), (b'yellow', 0)])

    ctx = AsyncNodeContext('mesh', 'name', 'node')
    mocker.patch('lemon.api.API.ctx', ctx)
    assert await anyone_listening('hello', 'yellow')


def test_get_ctx(mocker: "MockerFixture"):
    ctx = MagicMock()
    mocker.patch('lemon.api.API.ctx', ctx)

    assert get_ctx() == ctx
