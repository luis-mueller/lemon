import os
import pickle
import traceback
import psutil
import shutil
import click
import yaml
from prettytable import PrettyTable
from lemon.ctx import NodeContext
from lemon.build import InvalidLemonfileException, build_mesh
from lemon.health import get_health, init_health
from lemon.system import LogFileService, NodePIDNotFound, ProcessService
from lemon.utils import (
    Severity,
    Entity,
    bold_str,
    ensure_redis,
    severity_to_message,
    entity_to_message,
    get_resource
)


@click.group()
def cli():
    pass


@cli.command()
def build():
    """Build nodes and meshes defined in the local Lemonfile 🍋"""
    redis_client = ensure_redis()

    entity_to_message(
        Entity.Lemonfile, '🍋', 'Building locally')

    try:
        with open('Lemonfile.yml', 'r') as file:
            meshes = yaml.safe_load(file)

        for mesh in meshes:
            build_mesh(redis_client, mesh)
    except FileNotFoundError:
        severity_to_message(Severity.Error, "No Lemonfile detected")

    except InvalidLemonfileException:
        severity_to_message(Severity.Error, "Invalid Lemonfile")

    except Exception:
        traceback.print_exc()
        severity_to_message(Severity.Error, "Build failed")


def safe_load_mesh(redis_client, mesh):
    blob = redis_client.get(mesh)
    if blob:
        return pickle.loads(blob)

    entity_to_message(Entity.Mesh, mesh, "Upon loading")
    severity_to_message(Severity.Error, f"Mesh {mesh} not found")
    quit()


@cli.command()
@click.argument('mesh')
@click.option('-s', '--select', default=None, multiple=True)
@click.option('-x', '--exclude', default=[], multiple=True)
def start(mesh, select, exclude):
    """Start all nodes of mesh MESH"""
    redis_client = ensure_redis()
    nodes = safe_load_mesh(redis_client, mesh)

    entity_to_message(
        Entity.Mesh, mesh, "Starting nodes")

    for node in nodes:
        if select and node['name'] not in select:
            continue
        if node['name'] in exclude:
            continue

        severity_to_message(
            Severity.Information, f"Starting node {bold_str(node['name'])}")

        additional_args = []
        if 'with' in node:
            if not isinstance(node['with'], list):
                additional_args = [node['with']]
            else:
                additional_args = node['with']

        ctx = NodeContext.from_descriptor(mesh, node)

        if ProcessService.is_running(ctx):
            severity_to_message(
                Severity.Information, "Node still active")

            stop_node(mesh, node)

        process = ProcessService.start(ctx, additional_args)

        severity_to_message(Severity.Success, (
            f"{bold_str(node['name'])} started with PID {process.pid}")
        )


def stop_node(mesh, node):
    severity_to_message(
        Severity.Information, f"Stopping node {bold_str(node['name'])}")

    ctx = NodeContext.from_descriptor(mesh, node)

    try:
        ProcessService.stop(ctx)
        init_health(ctx)

        severity_to_message(Severity.Success,
                            f"{bold_str(node['name'])} stopped")

    except NodePIDNotFound:
        severity_to_message(Severity.Error,
                            bold_str(node['name']) +
                            " did not self-register")

        severity_to_message(
            Severity.Information,
            "Make sure to wrap your node into an @entrypoint")

    except psutil.NoSuchProcess:
        severity_to_message(Severity.Warning,
                            f"{bold_str(node['name'])} already stopped")


@cli.command()
@click.option('-s', '--select', default=None, multiple=True)
@click.option('-x', '--exclude', default=[], multiple=True)
@click.argument('mesh')
def stop(mesh: "str", select, exclude):
    """Stop all nodes of mesh MESH"""
    redis_client = ensure_redis()
    nodes = safe_load_mesh(redis_client, mesh)

    entity_to_message(
        Entity.Mesh, mesh, "Stopping nodes")

    for node in nodes:
        if select and node['name'] not in select:
            continue
        if node['name'] in exclude:
            continue

        stop_node(mesh, node)


@cli.command()
@click.argument('mesh')
def show(mesh):
    """Show health of mesh MESH"""
    redis_client = ensure_redis()

    entity_to_message(
        Entity.Mesh, mesh, 'Showing health')

    pretty_table = PrettyTable()
    pretty_table.field_names = map(
        bold_str, ['Instance', 'Node', 'Activity', 'Lifetime', 'Throughput'])

    for node in safe_load_mesh(redis_client, mesh):
        ctx = NodeContext.from_descriptor(mesh, node)
        pretty_table.add_row(get_health(ctx))

    print(pretty_table)


@cli.command()
@click.argument('name')
def create(name: "str") -> None:
    """Create starter code for a new node NAME"""
    package_name = name.replace('-', '_')

    entity_to_message(
        Entity.Node, name, 'Initializing.')

    try:
        os.makedirs(name)
        shutil.copyfile(get_resource('start.py'), f'{name}/{package_name}.py')

        with open(f'{name}/setup.py', 'w') as f:
            f.write(f"""from setuptools import setup
from pybind11.setup_helpers import Pybind11Extension, build_ext

setup(
    name='{name}',
    py_modules=['{package_name}'],
    entry_points = {{
        'console_scripts': ['{name} = {package_name}:start']}},
    ext_modules=[
        Pybind11Extension("{package_name}_cpp",
        sorted(["./{package_name}.cpp"]))
    ],
    cmdclass={{"build_ext": build_ext}},
)
""")

        with open(f'{name}/{package_name}.cpp', 'w') as f:
            f.write(f"""#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <iostream>

namespace py = pybind11;

void greet()
{{
    std::cout << "Hello 🍋 from inside C++!\n";
}}

PYBIND11_MODULE({package_name}_cpp, m)
{{
    m.def("greet", &greet);
}}
""")
        severity_to_message(Severity.Success,
                            f"{name} initalized.")

        severity_to_message(Severity.Information,
                            f"Build with {bold_str('pip install -e ' + name)}"
                            + f" or declare {bold_str(name)} in a Lemonfile.")

        print("\nGLHF!")

    except OSError as e:
        severity_to_message(Severity.Error,
                            f"Initialization failed: {e.strerror}")


@cli.command()
@click.argument('mesh')
@click.argument('node')
def log(mesh: "str", node: "str") -> None:
    """Show logs for NODE in MESH"""
    redis_client = ensure_redis()
    nodes = safe_load_mesh(redis_client, mesh)

    for node_ in nodes:
        if node_['name'] == node:
            ctx = NodeContext.from_descriptor(mesh, node_)
            with LogFileService.open(ctx, 'r') as file:
                print(''.join(file.readlines()))
