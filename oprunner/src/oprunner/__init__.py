"""oprunner: run ops in their own environments.

An op is an ordinary Python function carrying opspec's ``@op`` decorator,
which names the environment it needs. oprunner builds that environment with
Appose, starts a worker in it, and calls the op there; or tiles the call to
fit memory, or loops a 2-D op over a stack. The op itself never changes.

The top level of this package is deliberately austere -- standard library,
numpy and appose only -- because it is imported inside every op environment.
Anything heavier lives in a submodule that is imported lazily.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# oprunner's neighbours in a checkout are opspec and ophelper, kept beside it
# rather than in it: <checkout>/opspec/src, <checkout>/ophelper/src. A worker,
# the metadata service and Fiji all reach oprunner by putting its src/ on
# sys.path, so put their directories there too, and first, for the reason
# src/ goes first -- a checkout shadows the copy an environment installs. An
# installed oprunner has no such directories; there they are ordinary
# dependencies.
for _package in ("opspec", "ophelper"):
    _checkout = Path(__file__).resolve().parents[3] / _package / "src"
    if (_checkout / _package).is_dir() and str(_checkout) not in sys.path:
        sys.path.insert(0, str(_checkout))

__all__ = ["Runner", "Tiler", "discover", "run"]

_LAZY = {
    "Runner": "runner",
    "run": "runner",
    "discover": "discovery",
    "Tiler": "_tiling",
}


def __getattr__(name: str) -> Any:
    # Host-side machinery is imported on demand, so that merely importing
    # oprunner inside a worker stays cheap.
    module_name = _LAZY.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(f".{module_name}", __name__), name)
