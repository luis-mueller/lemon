from dataclasses import dataclass
import pickle
import redis
from lemon.utils import (
    Entity,
    Severity,
    bold_str,
    ensure_redis,
    entity_to_message,
    severity_to_message
)


@dataclass
class Parameter:
    topic: "str"
    redis_client: "redis.Redis"

    def __post_init__(self):
        self.initial_value = pickle.loads(self.redis_client.get(self.topic))

    def update(self, value):
        self.redis_client.publish(self.topic, pickle.dumps(value))
        return value


def topic_matches(
    topic: "str", mesh: "str", name: "str", param: "str"
):
    topic_parts = topic.split(':')
    if topic_parts[0] != '!param':
        return
    if mesh and topic_parts[1] != mesh:
        return
    if len(topic_parts) > 3 and name and topic_parts[2] != name:
        return
    if param and topic_parts[-1] != param:
        return
    if len(topic_parts) <= 3 and name:
        entity_to_message(
            Entity.Parameter, topic_parts[-1], "matched")

        severity_to_message(Severity.Warning,
                            "Parameter is shared, so"
                            + f"{bold_str('name')} is ignored!")
    return True


def parameters(
    mesh: "str" = None, name: "str" = None, param: "str" = None
) -> "list[Parameter]":
    """Returns a set of `py:class:Parameter` based on the details
    passed. E.g., if no arguments are passed, all available
    `py:class:Parameter` are returned.
    """
    redis_client = ensure_redis()

    str_topics = [str(topic, 'utf-8')
                  for topic in redis_client.pubsub_channels()]

    return [Parameter(topic, redis_client)
            for topic in str_topics
            if topic_matches(
                topic, mesh, name, param)]
