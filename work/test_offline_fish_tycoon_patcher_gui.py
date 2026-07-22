from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

import offline_fish_tycoon_patcher_gui as gui


class FishTycoonPatcherGuiTests(unittest.TestCase):
    def test_default_manifest_exists_in_source_layout(self) -> None:
        self.assertTrue(gui.default_manifest().is_file())

    def test_release_url_is_public_repository(self) -> None:
        self.assertEqual(
            gui.RELEASES_URL,
            "https://github.com/Lorsieab2/Fish-Tycoon-Fix-Patcher/releases",
        )

    def test_app_name_is_specific(self) -> None:
        self.assertEqual(gui.APP_NAME, "Fish Tycoon Fix Patcher")

    def test_paths_auto_populate_from_local_settings_like_vf2(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            expected = Path(temp) / gui.SETTINGS_FILE
            values = {"game_dir": r"C:\Games\Fish Tycoon", "output_dir": r"C:\Games\Fish Tycoon - Fixed"}
            gui.save_paths(values, expected)
            self.assertEqual(gui.load_paths(expected), values)
            self.assertEqual(gui.settings_path(Path(temp)), expected)
            self.assertEqual(gui.default_output_dir(values["game_dir"]), values["output_dir"])


if __name__ == "__main__":
    unittest.main()
