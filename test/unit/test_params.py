import pickle
from lemon.params import parameters
from pytest_mock import MockerFixture
from .utils import setup_client

PUBSUB_CHANNELS = [
    b'ch1',
    b'!param:mesh:node-name:ch2',
    b'!param:mesh:node-name:ch3',
    b'!param:mesh2:node-name:ch4',
    b'!param:mesh:other-node-name:ch3',
    b'!param:mesh:node-name:ch6',
]


def test_parameters_no_filter(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = PUBSUB_CHANNELS

    params = parameters()
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:node-name:ch2',
        '!param:mesh:node-name:ch3',
        '!param:mesh2:node-name:ch4',
        '!param:mesh:other-node-name:ch3',
        '!param:mesh:node-name:ch6'
    ]


def test_parameters_mesh_filter(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = PUBSUB_CHANNELS

    params = parameters(mesh='mesh')
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:node-name:ch2',
        '!param:mesh:node-name:ch3',
        '!param:mesh:other-node-name:ch3',
        '!param:mesh:node-name:ch6'
    ]


def test_parameters_mesh_and_name_filter(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = PUBSUB_CHANNELS

    params = parameters(mesh='mesh', name='node-name')
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:node-name:ch2',
        '!param:mesh:node-name:ch3',
        '!param:mesh:node-name:ch6'
    ]


def test_parameters_all_filter(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = PUBSUB_CHANNELS

    params = parameters(
        mesh='mesh', name='node-name', param='ch6')
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:node-name:ch6'
    ]


def test_parameters_shared(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = [
        b'!param:mesh:ch6'
    ]

    params = parameters(mesh='mesh', param='ch6')
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:ch6'
    ]


def test_parameters_shared_but_name_provided(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = [
        b'!param:mesh:ch6'
    ]

    params = parameters(
        mesh='mesh', name='node-name', param='ch6')
    topics = [p.topic for p in params]

    assert topics == [
        '!param:mesh:ch6'
    ]


def test_parameters_update(mocker: "MockerFixture"):
    client, _ = setup_client(mocker)

    client.get.return_value = pickle.dumps(0.5)
    client.pubsub_channels.return_value = PUBSUB_CHANNELS

    params = parameters(
        mesh='mesh', name='node-name', param='ch6')

    params[0].update(1.5)
    client.publish.assert_called_once_with(
        '!param:mesh:node-name:ch6', pickle.dumps(1.5))
