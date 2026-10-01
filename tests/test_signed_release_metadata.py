"""Authentic synthetic release manifests, no installer execution or network."""
import base64
import json
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from ugreen_app import release_signing as signing, update_check


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / "UgreenNASAdmin_setup_23.8.58.exe"
        self.file.write_bytes(b"synthetic installer, never executable")
        key = Ed25519PrivateKey.generate()
        self.private = key.private_bytes_raw()
        self.public = base64.b64encode(key.public_key().public_bytes_raw()).decode()
        self.raw = signing.sign_release_manifest(self.file, "23.8.58", "a"*40, self.private)

    def verify(self, raw=None, **kwargs):
        args = dict(current_version="23.8.57", expected_tag="v23.8.58", public_key_b64=self.public)
        args.update(kwargs)
        return signing.verify_release_manifest(self.file, self.raw if raw is None else raw, **args)

    def test_valid_release(self):
        self.assertEqual(self.verify(), (True, "ok"))

    def test_hash_only_signature_cannot_replace_metadata(self):
        self.assertFalse(self.verify(signing.signature_b64(signing.sign_file(self.file, self.private)).encode())[0])

    def test_changed_signed_fields_rejected(self):
        for field, value in (("version", "23.8.59"), ("asset", "other.exe"), ("source_commit", "b"*40),
                             ("sha256", "c"*64), ("size", 123), ("product", "Other")):
            env = json.loads(self.raw)
            env["release"][field] = value
            self.assertFalse(self.verify(json.dumps(env).encode())[0], field)

    def test_replayed_installer_cannot_claim_new_version(self):
        self.assertFalse(self.verify(expected_tag="v23.8.999")[0])
        self.assertFalse(self.verify(current_version="23.8.58")[0])
        self.assertFalse(self.verify(current_version="23.9.0")[0])

    def test_tampered_or_renamed_file_rejected(self):
        self.file.write_bytes(b"changed installer")
        self.assertFalse(self.verify()[0])
        renamed = self.file.with_name("UgreenNASAdmin_setup_23.8.59.exe")
        self.file.rename(renamed)
        self.file = renamed
        self.assertFalse(self.verify()[0])

    def test_wrong_signing_key_rejected(self):
        key = Ed25519PrivateKey.generate()
        public = base64.b64encode(key.public_key().public_bytes_raw()).decode()
        self.assertFalse(self.verify(public_key_b64=public)[0])

    def test_duplicate_oversized_or_malformed_json_rejected(self):
        for raw in (b"{}", b"[]", b'{"release":{}, "release":{}}', b"x"*8193, b"null"):
            self.assertFalse(self.verify(raw)[0])

    def test_versions_are_strict(self):
        for version in ("23.8.058", "23.8", "23.8.58beta", "23.8.58.1", "v23.8.58"):
            self.assertFalse(self.verify(current_version=version)[0])

    def test_api_selects_exact_metadata_asset(self):
        name = self.file.name
        release = update_check._release_from_api_payload({
            "tag_name": "v23.8.58", "assets": [
                {"name": name, "size": 35, "browser_download_url": "https://example.invalid/setup"},
                {"name": "wrong.release.json", "browser_download_url": "wrong"},
                {"name": name+".release.json", "browser_download_url": "expected"}]})
        self.assertEqual(release["asset_manifest_download_url"], "expected")
