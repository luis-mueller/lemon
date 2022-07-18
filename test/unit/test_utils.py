from asyncio import Future
from unittest.mock import MagicMock
from lemon.utils import ensure_redis
from pytest_mock import MockerFixture
import redis


def setup_client(mocker: "MockerFixture") -> "MagicMock":
    client = MagicMock(return_value=Future())
    return client, mocker.patch(
        'lemon.utils.redis.Redis', return_value=client)


def test_ensure_redis(mocker: "MockerFixture"):
    _, init = setup_client(mocker)

    ensure_redis()

    init.assert_called()


def test_ensure_redis_server_down(mocker: "MockerFixture"):
    client, init = setup_client(mocker)
    client.ping.side_effect = redis.exceptions.ConnectionError()
    popen = mocker.patch(
        'lemon.utils.subprocess.Popen'
    )
    ensure_redis()

    init.assert_called()
    popen.assert_called_once()
