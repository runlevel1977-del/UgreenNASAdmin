import json
from pathlib import Path
import tempfile
import unittest
from tools.secret_inventory import inventory


class SecretInventoryTests(unittest.TestCase):
    def test_reports_copies_without_disclosing_or_modifying_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'app_settings.json.bak'
            original=json.dumps({'email':{'smtp_pass':'synthetic-secret'},'telegram':{'bot_token':{'$ugreen_secret':'synthetic-reference'}}})
            path.write_text(original)
            report=inventory(folder)
            self.assertEqual(report['files'][0]['plaintext_fields'],1)
            self.assertEqual(report['files'][0]['vault_references'],1)
            self.assertNotIn('synthetic-secret',json.dumps(report))
            self.assertNotIn('synthetic-reference',json.dumps(report))
            self.assertEqual(path.read_text(),original)

    def test_malformed_file_is_not_claimed_clean(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'nas_admin_connection.json').write_text('broken')
            self.assertEqual(inventory(folder)['files'][0]['status'],'unreadable-or-unsupported')


if __name__ == '__main__': unittest.main()
