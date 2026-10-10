"""opspec.runtime: what an op calls while it runs (design 0004)."""

from opspec import runtime
from opspec.runtime import cancel_requested, progress, run


class Task:
    def __init__(self):
        self.updates = []
        self.cancel_requested = False

    def update(self, message=None, current=None, maximum=None):
        self.updates.append((message, current, maximum))


class Runner:
    def __init__(self):
        self.calls = []

    def run(self, op, args=None, **kwargs):
        self.calls.append(op.__name__)
        return op(**{**(args or {}), **kwargs})


def double(x):
    return 2 * x


def test_with_no_runner_an_op_is_a_plain_call():
    progress("nobody listening", 1, 2)  # does nothing, raises nothing
    assert cancel_requested() is False
    assert run(double, x=3) == 6
    assert run(double, {"x": 4}) == 8


def test_a_bound_task_gets_progress_and_says_when_to_stop():
    task = Task()
    token = runtime.bind_task(task)
    try:
        progress("Iteration 1 of 2", 0, 2)
        assert task.updates == [("Iteration 1 of 2", 0, 2)]
        assert cancel_requested() is False
        task.cancel_requested = True
        assert cancel_requested() is True
    finally:
        runtime.unbind_task(token)
    assert cancel_requested() is False


def test_a_bound_runner_runs_other_ops():
    runner = Runner()
    token = runtime.bind_runner(runner)
    try:
        assert run(double, x=5) == 10
    finally:
        runtime.unbind_runner(token)
    assert runner.calls == ["double"]
    assert run(double, x=1) == 2  # unbound: direct again
