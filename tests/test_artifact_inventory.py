from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools.artifact_inventory import native_inventory


class ArtifactInventoryTests(unittest.TestCase):
    def test_all_binary_suffixes_are_hashed_without_execution(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'nested').mkdir()
            for name in ('app.exe','nested/python.dll','nested/_ssl.pyd','readme.txt'):
                (root/name).write_bytes(b'synthetic-file')
            with patch('tools.artifact_inventory.file_version', return_value=None):
                report=native_inventory(root,{'fixture-package':'1.2.3'})
            self.assertEqual([row['file'] for row in report['native_files']],['app.exe','nested/_ssl.pyd','nested/python.dll'])
            self.assertTrue(all(len(row['sha256'])==64 for row in report['native_files']))
            self.assertTrue(all(row['review']=='version-unknown-review-required' for row in report['native_files']))
            self.assertEqual(report['python_packages'],{'fixture-package':'1.2.3'})


if __name__ == '__main__': unittest.main()
