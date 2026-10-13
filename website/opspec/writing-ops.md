# Writing ops

An op is a plain Python function.

## The decorator

```python
from opspec.op import Overlap, PeakMemory, op

@op                                  # runs where it's called
@op(env="skimage")                   # runs in an environment
@op(env="pytorch", exclusive=True)   # a worker of its own
@op(env="napari", main_thread=True)  # needs the main thread
```

Tiling hints, all optional. A runner tiles an input only when it would not
fit in memory:

```python
@op(
    env="cupy",
    tile=("image", "mask"),         # inputs cut into tiles, all the same way
    split=("y", "x"),               # axes a tile may be cut along; default any
    overlap=Overlap(param="psf", of="shape", scale=0.5),  # half the PSF
    peak_memory=PeakMemory(16, "float32", device="gpu"),  # 16 copies of the input
    merge="blend",                  # neighbours fade together
)
```

Simpler forms: `tile="image"`, `overlap=16` (pixels), `merge="crop"` (keep
each tile's core, drop the overlap).

## Annotations

| You write | It means |
|---|---|
| `ImageOf[np.ndarray]` | an image |
| `LabelsOf[np.ndarray]` | labels |
| `MasksOf`, `BoxesOf`, `PointsOf` | other roles |
| `Annotated[np.ndarray, Axes("y", "x")]` | 2-D; stacks are looped |
| `Axes("y", "x", "c?")` | optional channel axis |
| `Axes(variadic=True)` | any number of axes |
| `Annotated[float, {"min": 0, "max": 10}]` | a slider's range |
| an `Enum` | a dropdown |
| `Path` | a file picker |
| `X \| None = None` | optional input |
| `Out[ImageOf[np.ndarray]]` | caller allocates the output |
| `Mut[ImageOf[np.ndarray]]` | changed in place |
| `-> NamedTuple` | several named outputs |
| `-> LabelsOf[np.ndarray] \| None` | output may be missing |
| docstring `Args:` | tooltips |
| `Choices(cpu=..., gpu=...)` | pick an op |
| `ParamsFor("decon_op")` | the picked op's settings |

## Examples

### The smallest op

```python
import numpy as np
from opspec.op import op
from opspec.types import ImageOf

@op(env="skimage")
def smooth(image: ImageOf[np.ndarray], sigma: float = 2.0) -> ImageOf[np.ndarray]:
    """Gaussian blur.

    Args:
        image: The image to blur.
        sigma: Blur width, in pixels.
    """
    from skimage.filters import gaussian  # heavy imports go inside

    return gaussian(image, sigma)
```

### Labels out, with a dropdown and a slider

```python
from enum import Enum
from typing import Annotated

import numpy as np
from opspec.op import op
from opspec.types import ImageOf, LabelsOf

class Method(Enum):
    otsu = "otsu"
    li = "li"

@op(env="skimage")
def threshold(
    image: ImageOf[np.ndarray],
    method: Method = Method.otsu,
    blur: Annotated[float, {"min": 0.0, "max": 10.0}] = 1.0,
) -> LabelsOf[np.ndarray]:
    from skimage import filters, measure

    smoothed = filters.gaussian(image, blur)
    cutoff = getattr(filters, f"threshold_{method.value}")(smoothed)
    return measure.label(smoothed > cutoff)
```

### A 2-D op, run on stacks

```python
from typing import Annotated

import numpy as np
from opspec.op import Axes, op
from opspec.types import ImageOf, LabelsOf

@op(env="stardist")
def nuclei(
    image: Annotated[ImageOf[np.ndarray], Axes("y", "x")],
    probability: Annotated[float, {"min": 0.0, "max": 1.0}] = 0.5,
) -> LabelsOf[np.ndarray]:
    from stardist.models import StarDist2D

    model = StarDist2D.from_pretrained("2D_versatile_fluo")
    labels, _ = model.predict_instances(image, prob_thresh=probability)
    return labels
```

### Two outputs, one optional

```python
from typing import Annotated, NamedTuple

import numpy as np
from opspec.op import Axes, op
from opspec.types import ImageOf, LabelsOf

class NucleiAndCells(NamedTuple):
    nuclei: LabelsOf[np.ndarray]
    cells: LabelsOf[np.ndarray] | None  # None: nothing to show

@op(env="pytorch")
def nuclei_and_cells(
    image: Annotated[ImageOf[np.ndarray], Axes("y", "x", "c?")],
    find_cells: bool = True,
) -> NucleiAndCells:
    nuclei = np.zeros(image.shape[:2], np.int32)  # the model goes here
    cells = nuclei.copy() if find_cells else None
    return NucleiAndCells(nuclei, cells)
```

### Weights from a file

```python
from pathlib import Path

import numpy as np
from opspec.op import op
from opspec.types import ImageOf, LabelsOf

@op(env="pytorch")
def custom_model(image: ImageOf[np.ndarray], weights: Path) -> LabelsOf[np.ndarray]:
    import torch

    model = torch.load(weights, weights_only=False)
    return model(image)
```

### Writing into the caller's array

```python
import numpy as np
from opspec.op import Out, op
from opspec.types import ImageOf

@op(env="skimage")
def invert(image: ImageOf[np.ndarray], result: Out[ImageOf[np.ndarray]]) -> None:
    result[...] = image.max() - image
```

### Tiled on the GPU

```python
from typing import Annotated

import numpy as np
from opspec.op import Axes, Overlap, PeakMemory, op
from opspec.types import ImageOf

HALF_PSF = Overlap(param="psf", of="shape", scale=0.5)

@op(
    env="cupy",
    tile="image",
    split=("y", "x"),
    overlap=HALF_PSF,
    peak_memory=PeakMemory(16, "float32", pad=HALF_PSF, device="gpu"),
    merge="blend",
)
def deconvolve(
    image: Annotated[ImageOf[np.ndarray], Axes("z?", "y", "x")],
    psf: np.ndarray,
    iterations: int = 10,
) -> ImageOf[np.ndarray]:
    import cupy as cp

    ...  # Richardson-Lucy on the GPU
    return image
```

### A workflow: ops calling ops

```python
from collections.abc import Callable
from typing import Annotated

import numpy as np
from my_ops import deconvolve, gaussian_psf  # ops from above
from opspec.op import Choices, ParamsFor, op
from opspec.types import ImageOf

@op  # no environment: runs where it's called
def deconvolve_with_psf(
    image: ImageOf[np.ndarray],
    psf_op: Annotated[Callable, Choices(gaussian=gaussian_psf)] = gaussian_psf,
    psf_args: Annotated[dict | None, ParamsFor("psf_op")] = None,
    decon_op: Annotated[Callable, Choices(cpu=deconvolve)] = deconvolve,
    decon_args: Annotated[dict | None, ParamsFor("decon_op", binds=("image", "psf"))] = None,
) -> ImageOf[np.ndarray]:
    from opspec.runtime import run

    psf = run(psf_op, **(psf_args or {}))
    return run(decon_op, image=image, psf=psf, **(decon_args or {}))
```
