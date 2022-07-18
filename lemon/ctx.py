from dataclasses import dataclass
from lemon.utils import ensure_redis


@dataclass
class NodeContext:
    mesh: "str"
    name: "str"
    node: "str"

    def from_descriptor(mesh: "str", node: "dict") -> "NodeContext":
        return NodeContext(mesh, node['name'], node['node'])

    def __post_init__(self):
        self.renew()

    def renew(self):
        self.redis_client = ensure_redis()


@dataclass
class AsyncNodeContext(NodeContext):
    def renew(self):
        self.redis_client = ensure_redis(do_async=True)


ctx = None
