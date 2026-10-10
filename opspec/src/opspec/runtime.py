"""What an op calls while it runs: progress, cancel, other ops.

An op calls these; a runner plugs in. With no runner, ``progress`` does
nothing, ``cancel_requested`` is False, and ``run`` calls the op directly.
See docs/design/0004.
"""

from __future__ import annotations

from collections.abc import Callable
from contextvars import ContextVar, Token
from typing import Any, Protocol

__all__ = [
    "Task",
    "bind_runner",
    "bind_task",
    "cancel_requested",
    "progress",
    "run",
    "unbind_runner",
    "unbind_task",
]


class Task(Protocol):
    """Where a running op's progress goes. An Appose task is one."""

    cancel_requested: bool

    def update(
        self,
        message: str | None = None,
        current: int | None = None,
        maximum: int | None = None,
    ) -> None: ...


_task: ContextVar[Task | None] = ContextVar("opspec_task", default=None)
_runner: ContextVar[Any] = ContextVar("opspec_runner", default=None)


def progress(
    message: str | None = None,
    current: int | None = None,
    maximum: int | None = None,
) -> None:
    """Report progress to whoever is running this op, if anyone is."""
    task = _task.get()
    if task is not None:
        task.update(message=message, current=current, maximum=maximum)


def cancel_requested() -> bool:
    """Whether whoever is running this op has asked it to stop."""
    task = _task.get()
    return bool(task is not None and task.cancel_requested)


def run(op: Callable, args: dict | None = None, **kwargs: Any) -> Any:
    """Run another op: through the runner running this one, or directly."""
    runner = _runner.get()
    if runner is not None:
        return runner.run(op, args, **kwargs)
    return op(**{**(args or {}), **kwargs})


def bind_task(task: Task) -> Token:
    """For a runner: send progress to *task* until ``unbind_task``."""
    return _task.set(task)


def unbind_task(token: Token) -> None:
    _task.reset(token)


def bind_runner(runner: Any) -> Token:
    """For a runner: ``run`` goes through *runner* until ``unbind_runner``.

    *runner* needs a ``run(op, args, **kwargs)``.
    """
    return _runner.set(runner)


def unbind_runner(token: Token) -> None:
    _runner.reset(token)
