import importlib
import sys


def test_import_acmed_does_not_preload_main() -> None:
    sys.modules.pop("acmed", None)
    sys.modules.pop("acmed.main", None)

    importlib.import_module("acmed")

    assert "acmed.main" not in sys.modules
