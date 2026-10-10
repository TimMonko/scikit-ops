# oprunner

Runs ops -- Python functions declared with [opspec](../opspec) -- in their own
environments, built with [Appose](https://github.com/apposed/appose). It can
also tile a call to fit memory, and loop a 2-D op over a stack.

```python
from oprunner import Runner

with Runner() as runner:
    result = runner.run(some_op, image=image, sigma=2.0)
```

An op's environment is found beside the op's own files, in `envs/<id>/pixi.toml`.
