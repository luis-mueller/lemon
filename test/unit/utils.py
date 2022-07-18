from asyncio import Future
from unittest.mock import MagicMock
from pytest_mock import MockerFixture


def setup_client(mocker: "MockerFixture") -> "MagicMock":
    client = MagicMock(return_value=Future())
    return client, mocker.patch(
        'lemon.utils.redis.Redis', return_value=client)
