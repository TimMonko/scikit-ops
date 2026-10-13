"""Sphinx configuration for scikit-ops' documentation, set up like Appose's.

One site for every package here: opspec, ophelper, oprunner and the ops. The
design record is not part of it; it lives in ../docs/.
"""

project = "scikit-ops"

extensions = ["myst_parser", "sphinx_copybutton"]
myst_enable_extensions = ["colon_fence"]

exclude_patterns = ["_build"]

html_theme = "sphinx_rtd_theme"
html_title = "scikit-ops"
