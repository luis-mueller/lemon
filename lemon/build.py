import os
import pickle
from lemon.ctx import NodeContext
from lemon.health import init_health
from lemon.utils import (
    Entity,
    entity_to_message,
    bold_str,
    Severity,
    severity_to_message
)
import redis
from cerberus import Validator
import yaml

SCHEMA = {
    "mesh": {
        "type": "string",
        "required": True
    },
    "nodes": {
        "type": "list",
        "required": True,
        "schema": {
            "type": "dict",
            "required": True,
            "schema": {
                "name": {
                    "type": "string",
                    "required": True,
                    "regex": "[A-Za-z0-9_\\-]+"
                },
                "node": {
                    "type": "string",
                    "regex": "[A-Za-z0-9_\\-]+"
                },
                "from": {
                    "type": "string",
                    "required": True
                },
                "in": {
                    "type": "string"
                },
                "out": {
                    "type": "string"
                },
                "with": {
                    "type": [
                        "string",
                        "list"
                    ],
                    "schema": {
                        "type": "string"
                    }
                }
            }
        }
    }
}


class BuildFailureException(Exception):
    pass


class InvalidLemonfileException(Exception):
    pass


def display_validation(validator: "Validator"):
    print(yaml.dump(validator.errors))


def build_node(mesh: "str", node: "dict") -> None:
    severity_to_message(
        Severity.Information, f"Builing node {bold_str(node['name'])}")

    flags = ''
    if not node['from'].startswith('git+'):
        flags += ' -e'

    rtcode = os.system(f"python -m pip install{flags} {node['from']}")
    if rtcode != 0:
        raise BuildFailureException

    severity_to_message(
        Severity.Success, f"Built node {bold_str(node['name'])}")

    if 'node' not in node:
        node['node'] = node['name']

    ctx = NodeContext.from_descriptor(mesh, node)
    init_health(ctx)

    severity_to_message(
        Severity.Success,
        f"Registered node {bold_str(node['name'])} with persistency layer")


def build_mesh(redis_client: "redis.Redis", mesh: "dict") -> None:
    validator = Validator(SCHEMA)

    if not validator.validate(mesh):
        display_validation(validator)
        raise InvalidLemonfileException

    entity_to_message(
        Entity.Mesh, mesh['mesh'], "Building nodes")

    for node in mesh['nodes']:
        build_node(mesh['mesh'], node)

    redis_client.set(mesh['mesh'], pickle.dumps(mesh['nodes']))

    severity_to_message(
        Severity.Success,
        f"Registered mesh {bold_str(mesh['mesh'])} with persistency layer")
