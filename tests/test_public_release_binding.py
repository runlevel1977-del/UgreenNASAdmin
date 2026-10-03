import contextlib
import hashlib
import io
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tools import release_source_guard as guard
from tools import build_release_zip as bundle
from tools import sign_release_asset as signer


class PublicReleaseBindingTests(unittest.TestCase):
    state = {'source_commit':'a'*40, 'version':'1.2.3', 'tag':'v1.2.3', 'tag_exists':True}

    def test_lightweight_and_annotated_public_tags_match_exact_commit(self):
        ref='refs/tags/v1.2.3'
        for raw in (f"{'a'*40}\t{ref}\n", f"{'b'*40}\t{ref}\n{'a'*40}\t{ref}^{{}}\n"):
            with patch.object(guard,'release_source_state',return_value=self.state), \
                 patch.object(guard.subprocess,'run',return_value=SimpleNamespace(stdout=raw.encode())) as run:
                self.assertEqual(guard.public_release_state('unused','1.2.3'),self.state)
                self.assertIn(guard.PUBLIC_REPOSITORY,run.call_args.args[0])

    def test_missing_wrong_or_malformed_public_tag_rejected(self):
        for raw in ('', f"{'b'*40}\trefs/tags/v1.2.3\n", 'bad response', f"{'a'*40}\trefs/heads/main\n"):
            with self.subTest(raw=raw), patch.object(guard,'release_source_state',return_value=self.state), \
                 patch.object(guard.subprocess,'run',return_value=SimpleNamespace(stdout=raw.encode())):
                with self.assertRaises(ValueError): guard.public_release_state('unused','1.2.3')

    def test_no_local_tag_blocks_before_network(self):
        with patch.object(guard,'release_source_state',return_value=dict(self.state,tag_exists=False)), \
             patch.object(guard.subprocess,'run') as run:
            with self.assertRaises(ValueError): guard.public_release_state('unused','1.2.3')
        run.assert_not_called()

    def test_local_dist_cannot_bypass_build_record_or_replace_existing_release(self):
        with patch.object(bundle,'_pack_bundle') as pack, contextlib.redirect_stderr(io.StringIO()) as output:
            self.assertEqual(bundle.main_from_local_dist(),2)
        pack.assert_not_called(); self.assertIn('--build-dir',output.getvalue())

    def signing(self, source_hash='source-hash', commit='a'*40, changed=False):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'UgreenNASAdmin_setup_1.2.3.exe'; source.write_bytes(b'fixture')
            record={'source':{'source_commit':commit,'source_sha256':{'file':source_hash}},
                    'artifacts_sha256':{'installer/'+source.name:hashlib.sha256(b'other' if changed else b'fixture').hexdigest()}}
            with patch.object(signer,'public_release_state',return_value=self.state), \
                 patch.object(signer,'source_version',return_value='1.2.3'), \
                 patch.object(signer,'verify_record',return_value=record), \
                 patch.object(signer,'export_committed_sources',return_value={'source_sha256':{'file':'source-hash'}}):
                return signer.verified_signing_source(source,root/'build',root)

    def test_signing_binds_public_commit_sources_and_exact_installer_bytes(self):
        self.assertEqual(self.signing(),self.state)
        for options in ({'changed':True}, {'source_hash':'private-tree'}, {'commit':'c'*40}):
            with self.subTest(options=options), self.assertRaises(ValueError): self.signing(**options)

    def test_bundle_without_manifest_rejected_before_output_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            with patch.object(bundle,'RELEASE_DIR',root/'release'), self.assertRaises(ValueError):
                bundle._pack_bundle(ver='1.2.3',source_state=self.state,dist_dir=root,installer_out=root,manifest_src=None)
            self.assertFalse((root/'release').exists())


if __name__ == '__main__': unittest.main()
