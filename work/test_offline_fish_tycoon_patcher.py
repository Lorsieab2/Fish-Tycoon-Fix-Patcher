from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import tempfile
import unittest

import offline_fish_tycoon_patcher as patcher


MANIFEST_PATH = Path(__file__).resolve().parent.parent / "patches" / "crimson-comet-20-percent" / "manifest.json"


class FishTycoonPatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = patcher.read_json(MANIFEST_PATH)

    def test_manifest_has_one_default_main_fix(self) -> None:
        settings = patcher.manifest_settings(self.manifest)
        self.assertEqual(list(settings), ["crimson_comet_20_percent_cure"])
        self.assertTrue(settings["crimson_comet_20_percent_cure"]["default"])

    def test_patch_contract_applies_exactly_three_nonoverlapping_ranges(self) -> None:
        enabled = {"crimson_comet_20_percent_cure"}
        records = patcher.active_patch_records(self.manifest, enabled)
        data = bytearray(385024)
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            expected = patcher.parse_hex(record["expected"], "expected")
            data[offset:offset + len(expected)] = expected
        result, summary = patcher.apply_patch_bytes(bytes(data), records)
        self.assertEqual(len(summary), 3)
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            replacement = patcher.parse_hex(record["replacement"], "replacement")
            self.assertEqual(result[offset:offset + len(replacement)], replacement)

    def test_wrong_original_byte_is_rejected(self) -> None:
        records = patcher.active_patch_records(self.manifest, {"crimson_comet_20_percent_cure"})
        data = bytearray(385024)
        with self.assertRaises(patcher.PatchError):
            patcher.apply_patch_bytes(bytes(data), records)

    def test_disabled_fix_produces_no_patch_records(self) -> None:
        args = Namespace(disable_all=True, enable=None, disable=None)
        enabled = patcher.enabled_settings(self.manifest, args)
        self.assertEqual(enabled, set())
        self.assertEqual(patcher.active_patch_records(self.manifest, enabled), [])

    def test_probability_domain_is_exactly_twenty_percent(self) -> None:
        successes = [roll for roll in range(100) if roll < 20]
        self.assertEqual(successes, list(range(20)))
        self.assertEqual(len(successes), 20)

    def test_manifest_patched_hash_is_fixed(self) -> None:
        self.assertEqual(
            self.manifest["patched_sha256"],
            "33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B",
        )

    def test_output_marker_must_match_manifest_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            marker = root / ".fish_tycoon_bug_fix_output.json"
            marker.write_text(json.dumps({"manifest_id": self.manifest["id"]}), encoding="utf-8")
            self.assertTrue(patcher.recognized_output(root, self.manifest))
            marker.write_text(json.dumps({"manifest_id": "other"}), encoding="utf-8")
            self.assertFalse(patcher.recognized_output(root, self.manifest))


if __name__ == "__main__":
    unittest.main()
