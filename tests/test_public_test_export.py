"""Public export must retain its security regression corpus, not private data."""
from pathlib import Path
import unittest

from tools import sync_public_repo as sync


# These files exist only in the private tree and must stay off the public export.
_PRIVATE_ONLY_TESTS = frozenset({
    "test_transfer_hub_routes.py",
    "test_wake_sync_routes.py",
})


class PublicTestExportTests(unittest.TestCase):
    def test_every_public_test_and_fixture_survives_export(self) -> None:
        tests = Path(__file__).parent
        required = {
            path.name
            for path in tests.glob("*.py")
            if path.name != "__init__.py" and path.name not in _PRIVATE_ONLY_TESTS
        }
        self.assertFalse(required - sync.PUBLIC_TEST_FILES,
                         'Public tests/fixtures missing from explicit export allowlist: '
                         + ', '.join(sorted(required - sync.PUBLIC_TEST_FILES)))
        leaked = _PRIVATE_ONLY_TESTS & sync.PUBLIC_TEST_FILES
        self.assertFalse(
            leaked,
            "Private tests must not be exported: " + ", ".join(sorted(leaked)),
        )

if __name__ == '__main__':
    unittest.main()
