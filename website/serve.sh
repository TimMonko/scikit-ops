#!/usr/bin/env bash
# Build the docs and serve them at http://127.0.0.1:8000, rebuilding and
# refreshing the browser whenever a page is saved. Ctrl+C stops it.
#
#   website/serve.sh
#
# Sphinx is not a project dependency; uvx fetches it for this run, from
# requirements.txt, the list Read the Docs builds with. The site is written
# to website/_build/, which git ignores.
set -euo pipefail
cd "$(dirname "$0")"
uvx --from sphinx-autobuild --with-requirements requirements.txt \
    sphinx-autobuild . _build/html "$@"
