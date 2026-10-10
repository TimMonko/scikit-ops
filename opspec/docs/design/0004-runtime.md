# 0004 — What an op calls while it runs

## Background

Some ops report progress, stop when asked, or run other ops. In scikit-ops
they import `progress`, `cancel_requested` and `run` from `skop`, so a
collection of ops that wants them depends on scikit-ops: its runner, Appose
and all.

## Decision

The three are a protocol in opspec, `opspec.runtime`, standard library only.
An op calls them; a runner plugs in. Like `logging`: a library logs, and the
application decides where the messages go.

```python
from opspec.runtime import cancel_requested, progress, run

progress("Iteration 3 of 10", 2, 10)
if cancel_requested():
    ...
psf = run(gaussian_psf, size=64)
```

| Call | With a runner | With none |
|---|---|---|
| `progress(message, current, maximum)` | sent to the runner's task | does nothing |
| `cancel_requested()` | asks the runner's task | `False` |
| `run(op, args, **kwargs)` | the runner runs it | calls `op` directly |

A runner plugs in with `bind_task(task)` and `bind_runner(runner)`, each
undone with the token it returns. A task has `update(message, current,
maximum)` and `cancel_requested`, as an Appose task does.

## Consequences

- A collection of ops depends on opspec alone, and any runner can run it.
- With no runner, an op is a plain Python call, as before.
- Helpers that need numpy, such as building boxes or masks, are not part of
  this; they stay with whoever provides them.
