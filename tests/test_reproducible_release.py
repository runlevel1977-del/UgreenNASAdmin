import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from tools import reproducible_release as release


class ReproducibleReleaseTests(unittest.TestCase):
    def record(self, root, content=b"synthetic executable"):
        root.mkdir()
        (root/"app.exe").write_bytes(content)
        manifest = {"source": {"source_commit": "a"*40, "source_sha256": {"app.py": "b"*64}},
                    "environment": {"python": "3.12.0", "packages": {"example": "1.0"}},
                    "artifacts_sha256": release.tree_hashes(root)}
        (root/"BUILD_MANIFEST.json").write_text(json.dumps(manifest))
        return manifest

    def test_compare_identical_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"
            self.record(a); self.record(b)
            self.assertTrue(release.compare(a,b))

    def test_compare_different_bytes_is_not_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"
            self.record(a); self.record(b,b"different")
            with self.assertRaisesRegex(ValueError,"byte-identical"):
                release.compare(a,b)

    def test_tampering_or_extra_artifacts_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp)/"a"
            self.record(a)
            (a/"extra.dll").write_bytes(b"unexpected")
            with self.assertRaisesRegex(ValueError,"manifest"):
                release.verify_record(a)

    def test_same_outputs_different_inputs_are_not_proof(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp)/"a", Path(tmp)/"b"
            self.record(a); record=self.record(b)
            record["source"]["source_commit"]="c"*40
            (b/"BUILD_MANIFEST.json").write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,"inputs differ"):
                release.compare(a,b)

    def test_environment_drift_fails_before_build(self):
        with self.assertRaisesRegex(ValueError,"environment differs"):
            release.check_environment({"python":"3.12.0"},{"python":"3.12.1"})

    def test_every_dependency_pinned_exactly_and_sorted(self):
        self.assertEqual(release.requirements({"packages":{"zlib-fixture":"2.0","a-fixture":"1.0"}}),
                         "a-fixture==1.0\nzlib-fixture==2.0\n")

    def test_existing_output_preserved_without_running_tools(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(release.subprocess,"run") as run:
            root=Path(tmp);(root/"previous").write_bytes(b"keep")
            with self.assertRaisesRegex(ValueError,"must not exist"):
                release.build(root,root/"ISCC.exe",root)
            self.assertEqual((root/"previous").read_bytes(),b"keep")
            run.assert_not_called()

    def test_synthetic_complete_build_binds_source_environment_and_outputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"repo";root.mkdir()
            output=Path(tmp)/"result"
            lock={"platform":"win32","packages":{"fixture":"1.0"}}
            def export(repo, source, state):
                (source/"ugreen_app").mkdir()
                (source/"ugreen_app/nas_manager.py").write_text('__version__ = "1.2.3"')
                (source/"packaging").mkdir()
                (source/release.LOCK).write_text(json.dumps(lock))
                (source/release.PINS).write_text(release.requirements(lock))
                return dict(state,source_sha256=release.tree_hashes(source))
            def run(command, **kw):
                if "PyInstaller" in command:
                    out=Path(command[command.index("--distpath")+1])/"UgreenNASAdmin"
                    out.mkdir(parents=True);(out/"UgreenNASAdmin.exe").write_bytes(b"synthetic")
                elif command[0].endswith("ISCC.exe"):
                    out=Path(kw["cwd"])/"output";out.mkdir(parents=True)
                    (out/"UgreenNASAdmin_setup_1.2.3.exe").write_bytes(b"synthetic setup")
            with patch.object(release,"source_version",return_value="1.2.3"), \
                 patch.object(release,"release_source_state",return_value={"source_commit":"a"*40}), \
                 patch.object(release,"export_committed_sources",side_effect=export), \
                 patch.object(release,"environment",return_value=lock), \
                 patch.object(release.subprocess,"check_output",return_value=b"12345"), \
                 patch.object(release.subprocess,"run",side_effect=run):
                manifest=release.build(root,root/"ISCC.exe",output)
            self.assertEqual(release.verify_record(output),manifest)
            self.assertIn("portable/UgreenNASAdmin.exe",manifest["artifacts_sha256"])
            self.assertEqual(manifest["source"]["source_commit"],"a"*40)
