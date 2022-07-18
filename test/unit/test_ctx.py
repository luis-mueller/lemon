from unittest.mock import AsyncMock, MagicMock
from lemon.ctx import NodeContext
from pytest_mock import MockerFixture


def setup_client(mocker: "MockerFixture", do_async=False) -> "MagicMock":
    client = AsyncMock() if do_async else MagicMock()
    return client, mocker.patch(
        'lemon.ctx.ensure_redis', return_value=client)


def test_construct_from_descriptor(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    ctx = NodeContext.from_descriptor('mesh', {
        'name': 'a',
        'node': 'b',
        'from': './c',
        'in_channel': 'inc',
        'out_channel': 'outc',
        'with': 'w'
    })

    assert ctx.mesh == 'mesh'
    assert ctx.name == 'a'
    assert ctx.node == 'b'

    assert hasattr(ctx, 'redis_client')
    assert ctx.redis_client == client
