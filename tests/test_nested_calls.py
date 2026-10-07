"""A workflow's nested calls go through the runner its caller used.

``skop.run`` dispatches to an ambient runner, so the ops a workflow calls reuse
the workers it was started with, and report to whoever started it. The ambient
belongs to the *outermost* runner: a runner that wraps another must see those
calls, or nothing outside skop can observe a workflow -- a recorder, for one.
See ``skop.runner.ambient``.
"""

from __future__ import annotations

import skop
from skop import op
from skop.runner import Runner, ambient


@op()
def add(a: int, b: int) -> int:
    return a + b


@op()
def stops(a: int) -> bool:
    """A workflow that reports, then says whether it was asked to stop."""
    skop.progress("checking", 1, 2)
    return skop.cancel_requested()


@op()
def doubled(a: int) -> int:
    """A workflow: no env, so it runs here and calls add through skop.run."""
    return skop.run(add, {"a": a, "b": a})


class Recording:
    """A runner that wraps another and notes every op that goes through it."""

    def __init__(self, inner: Runner) -> None:
        self._inner = inner
        self.seen: list = []

    def run(self, fn, args=None, **kwargs):
        self.seen.append(fn)
        return self._inner.run(fn, args, **kwargs)


def test_a_workflow_runs_its_own_ops_here():
    assert Runner().run(doubled, {"a": 2}) == 4


def test_a_wrapper_sees_the_ops_a_workflow_calls():
    runner = Recording(Runner())
    with ambient(runner):
        assert runner.run(doubled, {"a": 3}) == 6
    assert runner.seen == [doubled, add]


def test_a_workflow_body_reports_to_and_hears_the_outer_task():
    # The caller holds the task the outermost ambient was given. The workflow
    # itself -- not only the ops it calls -- has to report to that task and
    # see a cancel aimed at it, or a wrapper's Cancel button reaches nothing
    # but the sub-op that happens to be running.
    heard, started = [], []
    runner = Recording(Runner())
    with ambient(runner, heard.append, started.append):
        (task,) = started
        task.cancel()
        assert runner.run(stops, {"a": 1}) is True
    assert [event.message for event in heard] == ["checking"]


def test_without_an_outer_ambient_the_runner_hands_out_its_own_task():
    started = []
    assert Runner().run(stops, {"a": 1}, on_start=started.append) is False
    assert len(started) == 1
