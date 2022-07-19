# Workshop: DVS-Integrator 🍋
Event-based vision image reconstruction based on [Scheerlinck et al., 2018](https://www.cedricscheerlinck.com/continuous-time-intensity-estimation) in Lemon.

This node uses `C++` for processing events one-by-one in `integrator.cpp` and `Python` for computing the leaky integrator in `integrator.py`.

Further, events are obtained via the [rosbag-player](https://github.com/pupuis/rosbag-player) and displayed via the [`image-server`](https://github.com/pupuis/image-server). The `image-server` provides a websocket to the excellent (and free) [Foxglove Studio](https://foxglove.dev/), so make sure to download the app or use it online in `Chrome`.

## Step 0: Install
Before getting started, make sure to have installed `Lemon` as described [here](https://github.com/pupuis/lemon#install).

Further, one way to work with this example is work directly within the cloned repository, i.e., run

```shell
cd lemon/examples/Event-based\ Vision/dvs-integrator/
```
and continue this tutorial from there.

## Step 1: Build the *integrate* mesh
The `Lemonfile.yml` already contains a mesh definiton `integrate` that connects the above nodes.
Run
```shell
lemon build
```
from the command line to install the nodes and configure the mesh with `Lemon`.

## Step 2: Prepare the data
First, download the [simulation-3planes](https://rpg.ifi.uzh.ch/datasets/eccv18_stereo_davis/bags/simulation_3planes.bag) dataset for event-based processing.

Now, in order to process this file with the `rosbag-player`, we need to convert the `.bag` file via `rosbag-convert` which comes pre-installed with the `rosbag-player`.
Run
```shell
rosbag-convert simulation_3planes.bag simulation_3planes_bag -m bag.mapping.yml
```
to convert the `.bag` file for further processing[^1].

## Step 3: Run the mesh
We are now ready to start the mesh by invoking
```shell
lemon start integrate
```
With
```shell
lemon show integrate
```
you can verify that all nodes are active.

## Step 4: Display the reconstructed images
Now, open `Foxglove Studio` -> `Open connection` -> `Foxglove WebSocket` and open the URL `ws://localhost:8765`. Then, configure two image panels listening to `/dvs/image` and `dvs/time_map`. For more information about running and configuring Foxglove Studio, see https://foxglove.dev/docs/studio.

## Step 5: Cleanup
Once you are done, you can let the nodes shutdown gracefully by running

```shell
lemon stop integrate
```

[^1]: You might want to only convert a subset of the provided topics or map them to new names (both of which we do with `bag.mapping.yml`). All this is accomplished by the `-m` option. Read more about it [here](https://github.com/pupuis/rosbag-player) or by running `rosbag-convert --help`.
