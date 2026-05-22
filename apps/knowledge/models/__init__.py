import importlib
import sys

if __name__ == "apps.knowledge.models":
    sys.modules[__name__] = importlib.import_module("knowledge.models")
else:
    from .knowledge import *
