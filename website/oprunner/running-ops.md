# Running ops

An op runs in its own environment, built the first time it is needed.

## The runner

```python
from oprunner import Runner
from skop.ops.smooth import gaussian

runner = Runner()
blurred = runner.run(gaussian, image=image, sigma=2.0)
```

Workers stay up between calls, so the second run is quick. `runner.close()`
stops them, or use `with Runner() as runner:` to stop them at the end.

## Calling an op directly

Every op is also a plain function, and can be called like one:

```python
blurred = gaussian(image, sigma=2.0)     # here, in this interpreter
```

It runs in your current environment, so the op's dependencies have to be
installed there. No worker, no other process, no thread: set a breakpoint and
step through it, or test it like any other function.

## Options to `run`

`run` takes the op's own arguments, and these as well. They say how to run
the op, never what it computes:

```python
runner.run(stardist2d_fluo, image=stack, prob_thresh=0.5,  # the op's arguments
           axes={"image": list("zyx")})                    # how to run it
```

| Option | What it does |
|---|---|
| `axes={"image": list("zyx")}` | what your array's axes are; the op's `Axes` annotation says what it takes, and a 2-D op is looped over z |
| `memory="2G"` | tiles the input to fit a budget |
| `tiler=Tiler(memory=0.5, overlap=16)` | tiling choices; `Tiler.off()` never tiles |
| `out=array` | writes the result there (numpy, zarr, HDF5) |
| `variant="cuda"` | uses a named pixi sub-environment |
| `on_progress=fn` | calls `fn` with each progress event |
| `on_start=fn` | calls `fn` with the running task, to cancel it |
| `args={"image": stack}` | the op's arguments as a dict, instead of as keywords |

`Runner(debug=True)` prints the worker's output and errors.

## Examples

### Progress

```python
from skop.ops.toy import slow_sum

def show(event):
    if event.message:                 # the first event only says it started
        print(event.message, event.current, event.maximum)

total = runner.run(slow_sum, image=image, on_progress=show)
```

### Cancel

```python
import threading

def cancel_soon(task):
    threading.Timer(2.0, task.cancel).start()

runner.run(slow_sum, image=image, steps=100, on_start=cancel_soon)
```

The op stops at its next `cancel_requested()` check; `slow_sum` returns the
sum so far.

### A 2-D op on a stack

The op says what it runs on, in its annotation:

```python
@op(env="stardist-tf")
def stardist2d_fluo(
    image: Annotated[ImageOf[np.ndarray], Axes("y", "x", "c?")],  # one plane
    ...
```

The caller says what the data is, in the call:

```python
from skop.ops.segment.stardist2d import stardist2d_fluo

labels = runner.run(stardist2d_fluo, image=stack, axes={"image": list("zyx")})
```

The runner matches the two: `y` and `x` go to the op, and it is called once
per `z`.

### Too big for memory

```python
from oprunner import Tiler
from skop.ops.deconvolve import richardson_lucy_cupy
from skop.ops.kernels.psf import gaussian_psf

psf = runner.run(gaussian_psf, xy_dim=64, xy_sigma=2.0, z_dim=32, z_sigma=3.0)

result = runner.run(richardson_lucy_cupy, image=volume, psf=psf, memory="4G")
result = runner.run(richardson_lucy_cupy, image=volume, psf=psf,
                    tiler=Tiler(tile_shape=(64, 512, 512)))
```

### Into a zarr array

```python
import zarr

store = zarr.open("result.zarr", mode="w", shape=volume.shape, dtype="float32")
runner.run(richardson_lucy_cupy, image=volume, psf=psf, out=store)
```

### Environments

```python
from skop.ops.segment.cellpose4 import cellpose4

env = runner.env_for(cellpose4)
env.config                            # .../envs/pytorch/pixi.toml
env.folder                            # ~/.local/share/appose/scikit-ops--pytorch

runner.environment_status("pytorch")  # "ready", "stale" or "missing"
runner.ensure_environment("pytorch")  # build it now, and say so
```

### Build progress

```python
def building(title, current, maximum):
    print(title, current, maximum)    # "Solving", "Installing conda packages", ...

runner.subscribe_build_progress(building)
```

### GPU memory

```python
runner.release("pytorch")                  # give back what the worker cached
runner.release("stardist-tf", close=True)  # TensorFlow only lets go when its worker stops
```

### Finding ops

```python
from oprunner import discover

specs, failures = discover("skop.ops")
for spec in specs:
    print(spec.name, spec.env)
for failure in failures:
    print(failure)                    # a module that would not import
```

### No runner of your own

```python
from oprunner import run

blurred = run(gaussian, image=image, sigma=2.0)  # a shared default runner
```
