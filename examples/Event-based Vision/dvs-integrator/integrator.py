import click
from lemon import entrypoint
from lemon.api import anyone_listening, parameter, publish, subscribe
from integrator_cpp import collect_events
import numpy as np


def minMaxLocRobust(image, discard):
    values = np.sort(image, axis=None)
    min_idx = int(.5*discard * values.shape[0])
    max_idx = int((1-.5*discard) * values.shape[0])
    return values[min_idx], values[max_idx]


def normalize(image):
    min_, max_ = minMaxLocRobust(image, 0.05)
    scale = 255 / (max_ - min_) if (min_ != max_) else 1
    return np.clip(scale * (image - min_), 0, 255)


def to_sec(timestamp):
    return timestamp['sec'] + 1e-9 * timestamp['nsec']


class Integrator:
    def __init__(self):
        self.alpha = 7.0
        self.time_last = 0

    async def set_alpha(self, alpha):
        print(f"New alpha: {alpha}")
        self.alpha = alpha

    def init_if_needed(self, msg):
        time_first = to_sec(msg['events'][0]['ts'])
        if not hasattr(self, 'image') or time_first < self.time_last:
            shape = (msg['height'], msg['width'])
            self.time_map = np.zeros(shape) + time_first
            self.image = np.zeros(shape)

    async def receive_events(self, msg):
        if not await anyone_listening('/dvs/image', '/dvs/time_map'):
            return

        self.init_if_needed(msg)

        collect_events(msg['events'], self.alpha, self.time_map, self.image)

        self.time_last = to_sec(msg['events'][-1]['ts'])
        decay = np.exp(-self.alpha * (self.time_last - self.time_map))
        image_out = self.image * decay

        ts = msg['events'][int(len(msg['events']) / 2)]['ts']
        await publish(
            '/dvs/image', (normalize(image_out), {'timestamp': ts}))
        await publish(
            '/dvs/time_map', (normalize(self.time_map), {'timestamp': ts}))


@click.option('-c', '--camera')
@entrypoint
async def start(camera):
    i = Integrator()

    await subscribe({
        camera: i.receive_events,
        **await parameter('alpha', 5.0, i.set_alpha)
    })
