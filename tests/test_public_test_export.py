"""Public export must retain its security regression corpus, not private data."""
from pathlib import Path
import unittest

from tools import sync_public_repo as sync


class PublicTestExportTests(unittest.TestCase):
    def test_every_public_test_and_fixture_survives_export(self):
        tests = Path(__file__).parent
        required = {path.name for path in tests.glob('*.py') if path.name != '__init__.py'}
        self.assertFalse(required - sync.PUBLIC_TEST_FILES,
                         'Public tests/fixtures missing from explicit export allowlist: '
                         + ', '.join(sorted(required - sync.PUBLIC_TEST_FILES)))

if __name__ == '__main__':
    unittest.main()
