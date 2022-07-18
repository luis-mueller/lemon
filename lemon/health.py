import time
from lemon.ctx import NodeContext, AsyncNodeContext
from lemon.utils import NodeActivity
from lemon.system import ProcessService
import pickle


def health_id(ctx: "NodeContext"):
    return f'{ctx.mesh}:{ctx.name}:health'


def get_time_passed(last_time):
    return time.time() - last_time


def get_throughput(time_passed):
    return '{:.2f} msg/s'.format(1 / time_passed)


def get_lifetime(start_time):
    return time.strftime('%H:%M:%S', time.gmtime(
        time.time() - start_time))


def get_health(ctx: "NodeContext"):
    activity, start_time, last_time = pickle.loads(
        ctx.redis_client.get(health_id(ctx)))

    is_running = ProcessService.is_running(ctx)

    if not (is_running and start_time and last_time):
        lifetime = ''
        throughput = ''
        if activity != NodeActivity.SHUTDOWN:
            activity = NodeActivity.FAILED
    else:
        time_passed = get_time_passed(last_time)
        throughput = get_throughput(time_passed)
        lifetime = get_lifetime(start_time)
        if time_passed > 5:
            activity = NodeActivity.WAITING

    return ctx.name, ctx.node, activity, lifetime, throughput


def init_health(ctx: "NodeContext"):
    data = pickle.dumps((NodeActivity.SHUTDOWN, None, None))
    ctx.redis_client.set(health_id(ctx), data)


class HealthService:
    def __init__(self):
        self.start_time = time.time()

    async def update(self, ctx: "AsyncNodeContext", activity: "NodeActivity"):
        data = pickle.dumps((activity, self.start_time, time.time()))
        await ctx.redis_client.set(health_id(ctx), data)
