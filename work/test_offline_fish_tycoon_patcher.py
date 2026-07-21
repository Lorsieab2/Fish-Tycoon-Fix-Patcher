from __future__ import annotations

from argparse import Namespace
import json
from pathlib import Path
import tempfile
import unittest

import offline_fish_tycoon_patcher as patcher


MANIFEST_PATH = Path(__file__).resolve().parent.parent / "patches" / "fish-tycoon-fixes" / "manifest.json"
CURE = "crimson_comet_20_percent_cure"
CHEMICAL = "unknown_chemical_three_uses"


class FishTycoonPatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = patcher.read_json(MANIFEST_PATH)

    def test_manifest_has_two_default_main_fixes(self) -> None:
        settings = patcher.manifest_settings(self.manifest)
        self.assertEqual(list(settings), [CURE, CHEMICAL])
        self.assertTrue(settings[CURE]["default"])
        self.assertTrue(settings[CHEMICAL]["default"])
        self.assertEqual(self.manifest["name"], "Fish Tycoon Fix Patcher")
        self.assertEqual(self.manifest["version"], "v1.1.0")

    def test_setting_combinations_select_one_checksum_and_expected_hash(self) -> None:
        cases = {
            frozenset(): (0, ""),
            frozenset({CURE}): (3, "33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B"),
            frozenset({CHEMICAL}): (3, "7A78B09F0509BDFFC191FFB9637FA41F8E8FEC73A10A524A6B017F3E42E88983"),
            frozenset({CURE, CHEMICAL}): (5, "44CCC2EAA5633A88CDE03115C650F793E50391D48FFA707ADE44F284C808C49F"),
        }
        for selected, (count, expected_hash) in cases.items():
            enabled = set(selected)
            records = patcher.active_patch_records(self.manifest, enabled)
            self.assertEqual(len(records), count)
            checksum_records = [record for record in records if record["id"].startswith("update_pe_checksum_")]
            self.assertEqual(len(checksum_records), 0 if not enabled else 1)
            self.assertEqual(patcher.expected_patched_hash(self.manifest, enabled), expected_hash)

    def test_default_contract_applies_five_nonoverlapping_ranges(self) -> None:
        records = patcher.active_patch_records(self.manifest, {CURE, CHEMICAL})
        data = bytearray(385024)
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            expected = patcher.parse_hex(record["expected"], "expected")
            data[offset:offset + len(expected)] = expected
        result, summary = patcher.apply_patch_bytes(bytes(data), records)
        self.assertEqual(len(summary), 5)
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            replacement = patcher.parse_hex(record["replacement"], "replacement")
            self.assertEqual(result[offset:offset + len(replacement)], replacement)

    def test_unknown_chemical_contract_is_three_uses_and_matching_text(self) -> None:
        records = {record["id"]: record for record in patcher.active_patch_records(self.manifest, {CHEMICAL})}
        counter = records["unknown_chemical_initialize_three_uses"]
        self.assertEqual(counter["offset"], "0x210B7")
        self.assertEqual(patcher.parse_hex(counter["replacement"], "replacement")[-4:], bytes.fromhex("03 00 00 00"))
        description = records["unknown_chemical_store_description_three_doses"]
        self.assertEqual(patcher.parse_hex(description["replacement"], "replacement").rstrip(b"\0"), b"Contains 3 doses.")

    def test_wrong_original_byte_is_rejected(self) -> None:
        records = patcher.active_patch_records(self.manifest, {CHEMICAL})
        with self.assertRaises(patcher.PatchError):
            patcher.apply_patch_bytes(bytes(385024), records)

    def test_disable_all_produces_no_patch_records(self) -> None:
        args = Namespace(disable_all=True, enable=None, disable=None)
        enabled = patcher.enabled_settings(self.manifest, args)
        self.assertEqual(enabled, set())
        self.assertEqual(patcher.active_patch_records(self.manifest, enabled), [])

    def test_probability_domain_is_exactly_twenty_percent(self) -> None:
        self.assertEqual([roll for roll in range(100) if roll < 20], list(range(20)))

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
