import sys
import os

root = os.path.abspath(os.path.dirname(__file__))
if root not in sys.path:
    sys.path.insert(0, root)

# Force-load the app package from the root, not as a sub-package
import importlib.util
for mod in ["__init__", "models", "auth", "main", "search", "output", "form"]:
    spec = importlib.util.spec_from_file_location(
        mod, os.path.join(root, f"{mod}.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod] = module
    spec.loader.exec_module(module)