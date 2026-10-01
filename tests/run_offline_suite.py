"""Run unittest cases and the fixture-free fan-curve functions without pytest."""
import importlib
from pathlib import Path
import sys
import unittest


def main():
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "tests"))
    suite = unittest.defaultTestLoader.discover(str(root / "tests"))
    fan = importlib.import_module("test_fan_curve")
    for name, function in sorted(vars(fan).items()):
        if name.startswith("test_") and callable(function):
            suite.addTest(unittest.FunctionTestCase(function))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
