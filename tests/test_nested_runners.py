"""A runner bound around a Runner sees the calls a workflow makes.

A recorder, a cache or a logger wraps oprunner's Runner and binds itself
with ``opspec.runtime.bind_runner``. When the Runner runs a workflow, the
ops that workflow calls must go through the wrapper too, or it sees only
the outer call. Every op here has no environment, so nothing is built.
"""

import numpy as np

import oprunner
from opspec.op import op
from opspec.runtime import bind_runner, bound_runner, run, unbind_runner


@op
def double(image: np.ndarray) -> np.ndarray:
    return image * 2


@op
def double_twice(image: np.ndarray) -> np.ndarray:
    return run(double, image=run(double, image=image))


@op
def nested(image: np.ndarray) -> np.ndarray:
    return run(double_twice, image=image)


class Watching:
    """Records each call, then hands it to the Runner it wraps."""

    def __init__(self, inner):
        self.inner = inner
        self.calls = []

    def run(self, fn, args=None, **kwargs):
        self.calls.append((fn.__name__, sorted(kwargs)))
        return self.inner.run(fn, args, **kwargs)


def _watched(runner, fn, **kwargs):
    watching = Watching(runner)
    token = bind_runner(watching)
    try:
        result = watching.run(fn, **kwargs)
    finally:
        unbind_runner(token)
    return watching, result


def test_bound_runner_is_none_with_nothing_bound():
    assert bound_runner() is None


def test_bound_runner_is_what_was_bound():
    watching = Watching(None)
    token = bind_runner(watching)
    try:
        assert bound_runner() is watching
    finally:
        unbind_runner(token)
    assert bound_runner() is None


def test_a_wrapper_sees_the_calls_inside_a_workflow():
    with oprunner.Runner() as runner:
        watching, result = _watched(runner, double_twice, image=np.ones(3))
    assert [name for name, _ in watching.calls] == [
        "double_twice",
        "double",
        "double",
    ]
    assert list(result) == [4, 4, 4]


def test_a_wrapper_sees_calls_two_workflows_deep():
    with oprunner.Runner() as runner:
        watching, result = _watched(runner, nested, image=np.ones(2))
    assert [name for name, _ in watching.calls] == [
        "nested",
        "double_twice",
        "double",
        "double",
    ]
    assert list(result) == [4, 4]


def test_the_workflow_s_progress_and_tiler_still_reach_its_ops():
    tiler = oprunner.Tiler(memory="1G")
    with oprunner.Runner() as runner:
        watching, _ = _watched(runner, double_twice, image=np.ones(2), tiler=tiler)
    inner_calls = [kwargs for name, kwargs in watching.calls if name == "double"]
    assert inner_calls
    for kwargs in inner_calls:
        assert {"on_progress", "on_start", "tiler"} <= set(kwargs)


def test_with_nothing_bound_a_workflow_runs_as_before():
    with oprunner.Runner() as runner:
        assert list(runner.run(double_twice, image=np.ones(2))) == [4, 4]
    assert bound_runner() is None
