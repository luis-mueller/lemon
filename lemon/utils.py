from enum import Enum
import subprocess
import os
import time
import redis.asyncio as aioredis
import redis


class Severity(Enum):
    Error = 1
    Warning = 2
    Information = 3
    Success = 4


def severity_to_message(severity: "Severity", message: "str") -> None:
    if severity == Severity.Error:
        print(color_str("   Error: ", Color.Red) + message)
    elif severity == Severity.Warning:
        print(color_str("   Warning: ", Color.Orange) + message)
    elif severity == Severity.Information:
        print(color_str("   Info: ", Color.White) + message)
    elif severity == Severity.Success:
        print(color_str("   Success: ", Color.Green) + message)


class Entity(Enum):
    Lemonfile = 1
    Mesh = 2
    Node = 3
    Parameter = 4


def entity_to_message(entity: "Entity", id: "str", message: "str"):
    if entity == Entity.Lemonfile:
        print(color_str(f"Lemonfile {bold_str(id)}: ", Color.Orange) + message)
    elif entity == Entity.Mesh:
        print(color_str(f"Mesh {bold_str(id)}: ", Color.Purple) + message)
    elif entity == Entity.Node:
        print(color_str(f"Node {bold_str(id)}: ", Color.Blue) + message)
    elif entity == Entity.Parameter:
        print(color_str(f"Parameter {bold_str(id)}: ", Color.Green) + message)


class Color(Enum):
    White = '\033[0m'  # white (normal)
    Red = '\033[31m'  # red
    Green = '\033[32m'  # green
    Orange = '\033[33m'  # orange
    Blue = '\033[34m'  # blue
    Purple = '\033[35m'  # purple


def color_str(string: "str", color: "Color"):
    return color.value + string + Color.White.value


def bold_str(text):
    return '\033[1m' + str(text) + '\033[0m'


def get_resource(resource: "str"):
    return os.path.dirname(os.path.realpath(__file__)) + (
        '/resources/' + resource)


def ensure_redis(do_async=False):
    client = redis.Redis(host='localhost', port=6379)
    try:
        client.ping()
    except redis.exceptions.ConnectionError:
        subprocess.Popen([
            'redis-server', '--daemonize', 'yes'
        ])
    time.sleep(.05)
    return (
        aioredis if do_async else redis).Redis(host='localhost', port=6379)


class NodeActivity(Enum):
    ACTIVE = color_str('ACTIVE', Color.Green)
    WAITING = color_str('WAITING', Color.Orange)
    FAILS = color_str('FAILS', Color.Red)
    SHUTDOWN = color_str('SHUTDOWN', Color.White)
    FAILED = color_str('FAILED', Color.Red)

    def __str__(self):
        return self.value
