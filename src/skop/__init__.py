"""skop: scikit-ops' collection of image-processing ops.

Each op is an ordinary Python function declared with opspec's ``@op``, in
``skop.ops.<namespace>``; its environment is in ``envs/<id>/pixi.toml``. Call
one directly, or run it in its own environment with oprunner::

    from oprunner import Runner
    from skop.ops.smooth import gaussian

    with Runner() as runner:
        blurred = runner.run(gaussian, image=image, sigma=2.0)

skop is the working name; the collection will be renamed before release.
"""
