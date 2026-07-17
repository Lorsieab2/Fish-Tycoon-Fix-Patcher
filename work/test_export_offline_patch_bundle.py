from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import export_offline_patch_bundle as exporter
import package_patcher_zip as packager


ROOT = Path(__file__).resolve().parent.parent


class ExportOfflinePatchBundleTests(unittest.TestCase):
    def test_export_matches_player_facing_vf2_style_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "Fish-Tycoon-Bug-Fix-Patcher-v1.0.0"
            written = exporter.export_bundle(ROOT, output)
            self.assertEqual(len(written), 10)
            self.assertTrue((output / "Launch_GUI.bat").is_file())
            self.assertTrue((output / "Apply_Patcher.bat").is_file())
            self.assertTrue((output / "How to Use.txt").is_file())
            self.assertTrue((output / "manifest.json").is_file())
            self.assertFalse(any(output.rglob("*.exe")))
            manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], "v1.0.0")
            self.assertEqual(manifest["patched_sha256"], "33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B")

    def test_zip_has_one_top_level_folder_and_no_game_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "Fish-Tycoon-Bug-Fix-Patcher-v1.0.0"
            archive = root / "Fish-Tycoon-Bug-Fix-Patcher-v1.0.0.zip"
            exporter.export_bundle(ROOT, output)
            self.assertEqual(packager.package(output, archive), 10)
            with zipfile.ZipFile(archive) as bundle:
                names = bundle.namelist()
            self.assertTrue(names)
            self.assertTrue(all(name.startswith(f"{output.name}/") for name in names))
            self.assertFalse(any(name.lower().endswith(".exe") for name in names))


if __name__ == "__main__":
    unittest.main()
