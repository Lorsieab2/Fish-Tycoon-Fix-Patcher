from __future__ import annotations

from pathlib import Path
import unittest

import offline_fish_tycoon_patcher_gui as gui


class FishTycoonPatcherGuiTests(unittest.TestCase):
    def test_default_manifest_exists_in_source_layout(self) -> None:
        self.assertTrue(gui.default_manifest().is_file())

    def test_release_url_is_public_repository(self) -> None:
        self.assertEqual(
            gui.RELEASES_URL,
            "https://github.com/Lorsieab2/Fish-Tycoon-Bug-Fix-Patcher/releases",
        )

    def test_app_name_is_specific(self) -> None:
        self.assertEqual(gui.APP_NAME, "Fish Tycoon Bug Fix Patcher")


if __name__ == "__main__":
    unittest.main()
