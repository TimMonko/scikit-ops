# 0021 — Op collections

**Status:** proposed. Nothing built.

`discover("skop.ops")` takes a package name, and that is the only way ops are
found. A third party can write a package of ops, but nothing finds it unless
the caller names it, and nothing tells `Runner` where its environments live.
This document is the mechanism for registering a collection of ops, and for
skop to register its own the same way.

It is deliberately **not** about naming. Op names and environment IDs stay one
global namespace; see [Not decided](#not-decided).

## What a collection is

An importable package of ops, plus the two things `Runner` needs that a package
name does not give it:

```python
@dataclass(frozen=True)
class Collection:
    name: str        # "skop"
    package: str     # "skop.ops"
    envs_dir: Path   # where its envs/<env-id>/pixi.toml recipes live
    root: Path       # what a worker puts on sys.path to import `package`
```

Today `Runner` has exactly one `root` and one `envs_dir`
([0002](0002-named-environments.md)), found by `_default_root` and
`_default_envs_dir`. A collection is those two, per package instead of per
runner.

## Registration

An entry point in the `skop.collections` group resolving to a `Collection`, or
a zero-argument callable returning one:

```toml
[project.entry-points."skop.collections"]
skop = "skop.ops:collection"
```

A callable rather than a bare package string, because the paths are the hard
part and belong with the code that knows them. For skop that is the
checkout-or-wheel rule `_default_envs_dir` already implements. A third party
writes its own, or uses a helper assuming `<package>/envs`.

`discover()` with no argument walks every registered collection with the
existing per-package walk. `discover(package)` stays, so an unregistered
package still works and tests need no registration.

## Entry points are host-only

A worker does not install skop. The init script puts `root` on its `sys.path`,
so inside a worker there is no distribution metadata and no entry points.
Resolving a collection name therefore happens on the host, and what crosses
into the worker is what already does: a package name (`host.describe(package)`)
and a path. Nothing in the worker should call `entry_points`.

## skop registers itself

The bundled ops are declared the same way a third party's would be. There is no
special case in discovery for `skop.ops`, so the wheel layout (`skop/envs` by
`force-include`) and the checkout layout both have to work through the
descriptor, and a third party exercises the path skop does.

One hazard. An editable install writes entry points when it is installed, so
the first checkout after this lands has no `skop` entry until `uv sync`. A stale
install must not report zero ops, which reads as every op having broken. When
the `skop` entry is missing, discovery includes `skop.ops` anyway and says so.

## What changes in the code

- `OpSpec` gains the collection it came from.
- `Runner` resolves `env_config`, `env_ids` and `_init_script` through the op's
  collection instead of one `envs_dir` and `root`.
- `LoadFailure` records its collection.
- A second collection declaring an op name already taken is reported as a
  failure naming both, rather than one silently winning the sort.

## Not decided

**Namespacing.** Anything can declare an op anywhere, and op names are one flat
namespace; `discover` sorts specs by bare name. Environment IDs are likewise
global, and Appose names the built environment `skop-<env-id>`, so two
collections shipping `envs/torch/` would share one built environment, whichever
recipe built it first. This document detects clashes and does not resolve them.
Whether names, environment IDs, or both should be qualified by collection, and
what front ends and workflows do with the qualified form, is open and bears on
more than discovery.

**Environment name and lock hash.** [0020](0020-reproducible-environments.md)
also wants to change the built environment's name. Any renaming here should be
done once, with that.
