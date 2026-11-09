"""Make the code importable as the `model` package from a clone with any folder name.

The modules import each other as `model.<name>` (they also live at model/ inside my portfolio
repo), so a plain `git clone` + `pytest` needs this alias to resolve them.
"""

import importlib.util
import pathlib
import sys

if "model" not in sys.modules:
    root = pathlib.Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location(
        "model", root / "__init__.py", submodule_search_locations=[str(root)]
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["model"] = module
    spec.loader.exec_module(module)
