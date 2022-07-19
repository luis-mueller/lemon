# Lightweight Event-Management On Nodes (Lemon) 🍋

Lemon is a lightweight event-management software that lets you easily compose, build and run
event-based applications.

## Install
You can install `Lemon` by running

```shell
git clone https://github.com/pupuis/lemon.git
pip install ./lemon
```

We recommend you to install `Lemon` in a virtual environment, e.g. with `conda`:

```shell
conda create -n lemon python=3.9
conda activate lemon
```

`Lemon` is tested on `python=3.9`. Read on to see a basic example, explaining the most important concepts of `Lemon`.

## Getting Started: Hello, 🍋!
Lemon uses a configuration file called the `Lemonfile.yml` to declare *meshes* of
*nodes* that run in the same application context.

For example
```yaml
- mesh: example
  nodes:
    - name: greeter
      from: ./greeter

    - name: receiver
      from: ./receiver
```
declares a mesh `example` with nodes `greeter` and `receiver`, located at `./greeter` and `./receiver`. Example implementations for those nodes could be

```python
# greeter/greeter.py
@entrypoint
async def main():
    await publish('greeter-artifact', {'Greeting': 'Hello, 🍋!'})
```

which publishes a message (which can be any python object) to topic `greeter-artifact` and

```python
# receiver/receiver.py
async def on_receive(message):
    greeting = message['Greeting']
    print(f'Received greeting: {greeting}')

@entrypoint
async def main():
    await subscribe({
        'greeter-artifact': on_receive
    })
```

which registers a handler `on_receive` to be called with any message published to topic `greeter-artifact`.

Now that the nodes are declared we need to make them installable to integrate with `Lemon`. For this we place a `setup.py` with the following content in both `./greeter` and `./receiver`:

```python
# greeter/setup.py
from setuptools import setup

setup(
    name='greeter',
    py_modules=['greeter'],
    entry_points = {
        'console_scripts': ['greeter = greeter:main']}
)
```
```python
# receiver/setup.py
from setuptools import setup

setup(
    name='receiver',
    py_modules=['receiver'],
    entry_points = {
        'console_scripts': ['receiver = receiver:main']}
)
```

Finally, we should have the following directory structure
```
Lemonfile.yml
greeter
    setup.py
    greeter.py
receiver
    setup.py
    receiver.py
```
and run
```shell
lemon build
```
to install the nodes and register the mesh `example` with `Lemon`.

If we now run
```shell
lemon start example
```
the nodes will be executed in the background. This is especially useful if we have a permanently running mesh with many components. However, since in our example the nodes process one event and then terminate, we can verify their work (i.e., `receiver`'s writing to stdout) via

```shell
lemon log example receiver
```
which gives us the stdout and stderr of the `receiver` node. The output should be:

```shell
Received greeting: Hello, 🍋!
```

We can always monitor the status of our mesh by running

```shell
lemon show example
```
which prints
```shell
Mesh example: Showing health
+---------------+---------------+----------+----------+------------+
|    Instance   |      Node     | Activity | Lifetime | Throughput |
+---------------+---------------+----------+----------+------------+
|   greeter     |   greeter     | SHUTDOWN |          |            |
|   receiver    |   receiver    | SHUTDOWN |          |            |
+---------------+---------------+----------+----------+------------+
```
