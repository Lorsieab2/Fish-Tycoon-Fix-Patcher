from __future__ import annotations

from argparse import Namespace
from itertools import combinations
import json
from pathlib import Path
import tempfile
import unittest

import build_universal_slots_patch as slots
import offline_fish_tycoon_patcher as patcher


MANIFEST_PATH = Path(__file__).resolve().parent.parent / "patches" / "fish-tycoon-fixes" / "manifest.json"
CURE = "crimson_comet_20_percent_cure"
CHEMICAL = "unknown_chemical_three_uses"
UNIVERSAL = "universal_supply_slots"


class FishTycoonPatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = patcher.read_json(MANIFEST_PATH)

    def test_manifest_has_three_default_main_fixes(self) -> None:
        settings = patcher.manifest_settings(self.manifest)
        self.assertEqual(list(settings), [CURE, CHEMICAL, UNIVERSAL])
        self.assertTrue(all(settings[key]["default"] for key in settings))
        self.assertEqual(self.manifest["name"], "Fish Tycoon Fix Patcher")
        self.assertEqual(self.manifest["version"], "v1.2.1")

    def test_all_seven_setting_combinations_have_one_checksum_and_hash(self) -> None:
        ids = [CURE, CHEMICAL, UNIVERSAL]
        for count in range(1, 4):
            for combo in combinations(ids, count):
                enabled = set(combo)
                records = patcher.active_patch_records(self.manifest, enabled)
                checksums = [r for r in records if r["id"].startswith("update_pe_checksum_")]
                self.assertEqual(len(checksums), 1, combo)
                self.assertEqual(len(patcher.expected_patched_hash(self.manifest, enabled)), 64)

    def test_disable_all_produces_no_patch_records(self) -> None:
        args = Namespace(disable_all=True, enable=None, disable=None)
        enabled = patcher.enabled_settings(self.manifest, args)
        self.assertEqual(enabled, set())
        self.assertEqual(patcher.active_patch_records(self.manifest, enabled), [])

    def test_payload_contract_and_unknown_variants(self) -> None:
        payload1, labels1 = slots.build_payload(1)
        payload3, labels3 = slots.build_payload(3)
        self.assertEqual(labels1, labels3)
        self.assertEqual(len(payload1), len(payload3))
        differences = [i for i, pair in enumerate(zip(payload1, payload3)) if pair[0] != pair[1]]
        self.assertEqual(len(differences), 1)
        self.assertEqual((payload1[differences[0]], payload3[differences[0]]), (1, 3))
        self.assertIn(bytes.fromhex("6A 01 68 EC 00 00 00"), payload1[:labels1["purchase_confirmed"]])
        self.assertIn(bytes.fromhex("89 5E 1C"), payload1)  # selected physical slot is restored

    def test_unknown_chemical_runtime_reset_is_removed(self) -> None:
        for enabled in ({CHEMICAL}, {UNIVERSAL}, {CHEMICAL, UNIVERSAL}):
            records = patcher.active_patch_records(self.manifest, enabled)
            reset_records = [r for r in records if r["offset"] == "0x210B7"]
            self.assertEqual(len(reset_records), 1)
            self.assertEqual(patcher.parse_hex(reset_records[0]["replacement"], "replacement"), b"\x90" * 10)

    def test_universal_setting_has_exact_supported_item_contract(self) -> None:
        setting = patcher.manifest_settings(self.manifest)[UNIVERSAL]
        text = setting["description"]
        self.assertIn("eight supported", text)
        records = patcher.active_patch_records(self.manifest, {UNIVERSAL})
        ids = {r["id"] for r in records}
        for egg in ("common", "unusual", "rare"):
            self.assertIn(f"stack_{egg}_egg_uses", ids)
        self.assertIn("install_universal_slots_payload_unknown_one", ids)
        self.assertNotIn("install_universal_slots_payload_unknown_three", ids)

    def test_manifest_pins_original_resource_section_for_icon_preservation(self) -> None:
        resource = self.manifest["target"]["resource_section"]
        self.assertEqual(resource["name"], ".rsrc")
        self.assertGreater(resource["size"], 0)
        self.assertEqual(len(resource["sha256"]), 64)

    def test_default_contract_applies_nonoverlapping_ranges(self) -> None:
        records = patcher.active_patch_records(self.manifest, {CURE, CHEMICAL, UNIVERSAL})
        data = bytearray(385024)
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            expected = patcher.parse_hex(record["expected"], "expected")
            data[offset:offset + len(expected)] = expected
        result, summary = patcher.apply_patch_bytes(bytes(data), records)
        self.assertEqual(len(summary), len(records))
        for record in records:
            offset = patcher.parse_int(record["offset"], "offset")
            replacement = patcher.parse_hex(record["replacement"], "replacement")
            self.assertEqual(result[offset:offset + len(replacement)], replacement)

    def test_wrong_original_byte_is_rejected(self) -> None:
        with self.assertRaises(patcher.PatchError):
            patcher.apply_patch_bytes(bytes(385024), patcher.active_patch_records(self.manifest, {UNIVERSAL}))

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
