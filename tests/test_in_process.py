"""oprunner.InProcess: the runner protocol, with no environment.

Each op here declares an environment that is never built: InProcess calls
it in this process, so nothing here needs pixi.
"""

from typing import Annotated

import numpy as np
import pytest

import oprunner
import opspec.plan
from opspec.op import Axes, op
from opspec.runtime import (
    bind_runner,
    cancel_requested,
    progress,
    run,
    unbind_runner,
)


@op(env="never-built")
def add_one(image: np.ndarray) -> np.ndarray:
    return image + 1


@op(env="never-built")
def plane_sum(image: Annotated[np.ndarray, Axes(list("yx"))]) -> np.ndarray:
    return np.full(image.shape, image.sum())


@op(env="never-built")
def reports(image: np.ndarray) -> np.ndarray:
    progress("half way", 1, 2)
    return image * int(not cancel_requested())


def test_runs_the_op_here_with_args_or_kwargs():
    runner = oprunner.InProcess()
    assert list(runner.run(add_one, {"image": np.zeros(2)})) == [1, 1]
    assert list(runner.run(add_one, image=np.zeros(2))) == [1, 1]


def test_checks_arguments_like_a_runner():
    runner = oprunner.InProcess()
    with pytest.raises(TypeError, match="no parameter"):
        runner.run(add_one, image=np.zeros(2), sigma=1)
    with pytest.raises(TypeError, match="missing required"):
        runner.run(add_one)


def test_axes_loop_a_2d_op_over_a_stack():
    stack = np.stack([np.ones((2, 2)), 2 * np.ones((2, 2))])
    result = oprunner.InProcess().run(
        plane_sum, image=stack, axes={"image": list("zyx")}
    )
    assert result.shape == (2, 2, 2)
    assert result[0, 0, 0] == 4 and result[1, 0, 0] == 8


@op
def host_plane_sum(image: Annotated[np.ndarray, Axes(list("yx"))]) -> np.ndarray:
    return np.full(image.shape, image.sum())


def test_axes_apply_to_an_op_with_no_env_too():
    stack = np.ones((3, 2, 2))
    result = oprunner.InProcess().run(
        host_plane_sum, image=stack, axes={"image": list("zyx")}
    )
    assert result.shape == (3, 2, 2) and result[0, 0, 0] == 4


def test_an_explicit_plan_is_honoured():
    stack = np.ones((3, 2, 2))
    plan = opspec.plan.plan(plane_sum, "image", stack, list("zyx"))
    result = oprunner.InProcess().run(plane_sum, image=stack, plans={"image": plan})
    assert result.shape == (3, 2, 2)


def test_progress_and_cancel_reach_the_caller():
    events, started = [], []
    runner = oprunner.InProcess()
    result = runner.run(
        reports,
        image=np.ones(2),
        on_progress=events.append,
        on_start=started.append,
    )
    assert [e.message for e in events] == ["half way"]
    assert list(result) == [1, 1]

    def cancel_first(task):
        task.cancel()

    cancelled = runner.run(reports, image=np.ones(2), on_start=cancel_first)
    assert list(cancelled) == [0, 0]


def test_out_receives_a_single_array_result():
    target = np.zeros(2)
    returned = oprunner.InProcess().run(add_one, image=np.zeros(2), out=target)
    assert returned is target
    assert list(target) == [1, 1]


def test_tiling_is_refused_not_ignored():
    runner = oprunner.InProcess()
    with pytest.raises(ValueError, match="does not tile"):
        runner.run(add_one, image=np.zeros(2), memory="1G")
    with pytest.raises(ValueError, match="does not tile"):
        runner.run(add_one, image=np.zeros(2), tiler=oprunner.Tiler())
    # Off is fine: it asks for nothing.
    runner.run(add_one, image=np.zeros(2), tiler=oprunner.Tiler.off())
    runner.run(add_one, image=np.zeros(2), memory="off")


@op
def calls_reports(image: np.ndarray) -> np.ndarray:
    progress("calling")
    return run(reports, image=image)


def test_a_workflow_s_calls_report_to_the_same_task():
    events = []
    result = oprunner.InProcess().run(
        calls_reports, image=np.ones(2), on_progress=events.append
    )
    assert [e.message for e in events] == ["calling", "half way"]
    assert list(result) == [1, 1]


def test_a_wrapper_bound_around_it_sees_the_nested_call():
    seen = []

    class Watching:
        def __init__(self, inner):
            self.inner = inner

        def run(self, fn, args=None, **kwargs):
            seen.append(fn.__name__)
            return self.inner.run(fn, args, **kwargs)

    watching = Watching(oprunner.InProcess())
    token = bind_runner(watching)
    try:
        watching.run(calls_reports, image=np.ones(2))
    finally:
        unbind_runner(token)
    assert seen == ["calls_reports", "reports"]


def test_a_variant_is_accepted_and_has_no_effect():
    assert list(
        oprunner.InProcess().run(add_one, image=np.zeros(1), variant="cuda")
    ) == [1]
