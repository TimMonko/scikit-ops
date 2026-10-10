"""ophelper stands alone: no runner, no skop."""

import subprocess
import sys


def test_importing_ophelper_does_not_import_skop():
    code = (
        "import sys, ophelper.boxes, ophelper.masks, ophelper.assets;"
        "print(any(m == 'skop' or m.startswith('skop.') for m in sys.modules))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == "False", out.stderr
