import asyncio
import pickle
import sys
import click
from lemon.ctx import AsyncNodeContext
from lemon.health import HealthService, NodeActivity
from lemon.utils import (
    Entity,
    Severity,
    bold_str,
    severity_to_message,
    entity_to_message,
)
from lemon.system import ProcessService
import redis
from redis.asyncio.client import PubSub


class API:
    ctx: "AsyncNodeContext"
    health_service: "HealthService"


def get_ctx() -> "AsyncNodeContext":
    return API.ctx


async def self_register():
    entity_to_message(Entity.Node, API.ctx.node, "starting")

    await ProcessService.self_register(API.ctx)

    severity_to_message(Severity.Success, bold_str(API.ctx.node) +
                        " self-registered for process monitoring")


def run_node(entrypoint, cleanup):
    """Adapted from: https://github.com/foxglove/ws-protocol/'s
    ``run_cancellable``. Didn't want to make ``foxglove-webserver``
    a dependency just for this function.
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(entrypoint)

    try:
        loop.run_until_complete(self_register())
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        task.cancel()
        loop.run_until_complete(asyncio.wait((task,), timeout=1))
    finally:
        loop.run_until_complete(loop.create_task(cleanup))


def entrypoint(fn):
    """Decorator function to indicate the entrypoint of a node.
    This registers the node properly with Lemon's `process
    monitoring`. Note that unlike :py:func:`lemon.api.subscribe`,
    the entrypoint function is not running on init and must be properly
    called from within python. If the node is called without the second
    argument, indicating a mesh, the node should be run without the
    lemon context.

    **Example**

    .. highlight:: python
    .. code-block:: python

        @entrypoint
        async def start():
            ...

        # Call from somewhere
        if __name__ == '__main__':
            start()

    The entrypoint turns the start of your node into a CLI via the ``click``
    API. You can further extend the CLI of your node by extending your
    callback with custom decorators.

    **Example**

    .. highlight:: python
    .. code-block:: python

        @click.option('-o', '--option')
        @entrypoint
        async def start(option):
            ...

        # Call from somewhere
        if __name__ == '__main__':
            start()

    will expose the following CLI: ``node mesh -o/--option ...
    The ``click`` API allows an arbitrary composition of such
    options and additional CLI arguments.

    :param fn: Function to declare as the entrypoint.
    """

    @click.command()
    @click.argument('mesh')
    @click.option('-n', '--name', default=None)
    def _entrypoint(mesh, name, *args, **kwargs):
        node = sys.argv[0].split('/')[-1]
        name = node if not name else name
        API.ctx = AsyncNodeContext(mesh, name, node)
        API.health_service = HealthService()

        async def cleanup():
            print()
            await API.health_service.update(API.ctx, NodeActivity.SHUTDOWN)
            await API.ctx.redis_client.close()

        run_node(fn(*args, **kwargs), cleanup())
    return _entrypoint


async def update_subscribe(pubsub_client: "PubSub", topic_to_fn):
    message = await pubsub_client.get_message(True)
    if message:
        callback = topic_to_fn[message['channel'].decode('utf8')]
        await callback(pickle.loads(message['data']))
        await API.health_service.update(API.ctx, NodeActivity.ACTIVE)


async def subscribe(topic_to_fn: "dict[str,]"):
    """*Subscribe* function to register a set of topic-to-callback pairs
    for subscription. It is important to subscribe to every topic at once
    via this function, so that the asynchronous processing can kick in.

    **Example**

    .. highlight:: python
    .. code-block:: python

        async def image_hook(image):
            ...

        await subscribe({'image': image_hook})

    listens to the *image* topic and calls ``image_hook`` on new messages.

    It might happen that your node is processing incoming events too slowly.
    In this case the subscription will successively drop events until
    it can keep up with the event stream.

    :param topic_to_fn: Mapping of topics to callback.
    """
    pubsub_client = API.ctx.redis_client.pubsub()
    await pubsub_client.subscribe(*topic_to_fn.keys())

    count = 0
    nth_message = 1

    await API.health_service.update(API.ctx, NodeActivity.ACTIVE)
    while True:
        await asyncio.sleep(1e-9)
        try:
            await update_subscribe(pubsub_client, topic_to_fn)
        except redis.exceptions.ConnectionError:
            API.ctx.renew()
            pubsub_client = API.ctx.redis_client.pubsub()
            await pubsub_client.subscribe(*topic_to_fn.keys())
            nth_message += 1

        count += 1


async def publish(topic, value):
    """*Publish* function with a hooked-in redis client. Allows for users
    to call stateless (i.e., no init required), but does not require to set
    up redis client for a every call. The ``value`` is pickled before
    transmission and can therefore assume any valid python object.

    **Example**

    .. highlight:: python
    .. code-block:: python

        # Here, the client is initalized once
        from lemon import publish

        async def start():
            for i in range(10):
                await publish('number', i)

    :param topic: Topic to publish to.
    :param value: Value to publish. Can be any python object.
    """
    await API.health_service.update(API.ctx, NodeActivity.ACTIVE)
    await API.ctx.redis_client.publish(topic, pickle.dumps(value))


async def parameter(name, value, fn, shared=False):
    """Helper function to add a parameter to a subscribing node. Parameters
    are special types of subscriptions that update some state in a node
    and are exposed via a dedicated API (see more below).

    **Example**

    .. highlight:: python
    .. code-block:: python

        class StatefulNode:
            async def update_ratio(self, ratio):
                self.ratio = ratio

        node = StatefulNode()

        subscribe(
            **await parameter('ratio', 0.5, node.update_ratio)
        )

    where ``ratio`` is initialized with the initial value 0.5 (you don't
    need to do this yourself) and is subsequently updated.

    For more information about how to control the parameter from outside of
    the node, see :py:func:`lemon.params.parameters`

    :param name: Name of the parameter.
    :param value: Initial value of the parameter. Can be any python object.
    :param fn: Callback function that updates the value
    :param shared: Parameters can be shared across a mesh. Set ``shared`` to
        True if you want to use these kinds of global variables.
    """
    private_id = f'{API.ctx.name}:' if not shared else ''

    topic = f'!param:{API.ctx.mesh}:{private_id}{name}'
    await API.ctx.redis_client.set(topic, pickle.dumps(value))
    await fn(value)
    return {topic: fn}


async def anyone_listening(*topics) -> "bool":
    """Helper function to determine whether the given topic has at least
    one subscriber.

    :param topics: Topics to check. Returns true if any of the topics is
        subscribed to.
    """
    numsub = await API.ctx.redis_client.pubsub_numsub(*topics)
    return any([num for _, num in numsub])
