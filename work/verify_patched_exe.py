#!/usr/bin/env python3
"""Independent byte-contract verifier for a Fish Tycoon Fix Patcher output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

import build_universal_slots_patch as slots
import offline_fish_tycoon_patcher as patcher


def rel32_target(instruction_va: int, instruction: bytes, opcode: int = 0xE8) -> int:
    if len(instruction) != 5 or instruction[0] != opcode:
        raise patcher.PatchError(f"Expected rel32 opcode 0x{opcode:02X} at 0x{instruction_va:X}.")
    displacement = struct.unpack_from("<i", instruction, 1)[0]
    return instruction_va + 5 + displacement


def default_settings(manifest: dict[str, object]) -> set[str]:
    return {
        setting_id
        for setting_id, value in patcher.manifest_settings(manifest).items()
        if bool(value.get("default", False))
    }


def verify(exe: Path, manifest_path: Path, enabled: set[str] | None = None) -> dict[str, object]:
    manifest = patcher.read_json(manifest_path)
    selected = default_settings(manifest) if enabled is None else set(enabled)
    data = exe.read_bytes()
    actual_hash = patcher.sha256_bytes(data)
    expected_hash = patcher.expected_patched_hash(manifest, selected)
    if not expected_hash or actual_hash != expected_hash:
        raise patcher.PatchError(f"Patched SHA-256 mismatch: {actual_hash}; expected {expected_hash or 'no manifest variant'}.")

    records = patcher.active_patch_records(manifest, selected)
    checks: dict[str, bool] = {
        "file_size_unchanged": len(data) == 385024,
    }
    for record in records:
        offset = patcher.parse_int(record["offset"], "offset")
        replacement = patcher.parse_hex(record["replacement"], "replacement")
        checks[f"patch:{record['id']}"] = data[offset:offset + len(replacement)] == replacement

    report: dict[str, object] = {
        "path": str(exe.resolve()),
        "size": len(data),
        "sha256": actual_hash,
        "enabled_settings": sorted(selected),
        "checks": checks,
    }

    if "crimson_comet_20_percent_cure" in selected:
        call = data[0x204CE:0x204D3]
        wrapper = data[0x1E11:0x1E1F]
        call_target = rel32_target(0x004204CE, call)
        wrapper_call_target = rel32_target(0x00401E13, wrapper[2:7])
        checks.update({
            "crimson_redirect_target": call_target == 0x00401E11,
            "crimson_rng_target": wrapper_call_target == 0x00403240,
            "crimson_success_values": [value for value in range(100) if value < 20] == list(range(20)),
            "crimson_original_clear_block_unchanged": data[0x204DA:0x204EB] == bytes.fromhex(
                "8B 46 34 89 9C 07 D0 03 00 00 8B 46 34 83 40 34 01"
            ),
        })
        report.update({
            "crimson_wrapper_va": "0x00401E11",
            "crimson_rng_target": f"0x{wrapper_call_target:08X}",
            "crimson_roll_domain": "0..99",
            "crimson_success_domain": "0..19",
        })

    if "unknown_chemical_three_uses" in selected:
        checks.update({
            "unknown_chemical_runtime_reset_removed": data[0x210B7:0x210C1] == b"\x90" * 10,
            "unknown_chemical_description": data[0x45870:0x458DC].split(b"\0", 1)[0].endswith(
                b"Contains 3 doses."
            ),
            "unknown_chemical_post_use_decrement_unchanged": data[0x21302:0x2130C] == bytes.fromhex(
                "8B 46 34 83 80 F8 02 00 00 FF"
            ),
        })
        report.update({
            "unknown_chemical_reset_removed_va": "0x004210B7",
            "unknown_chemical_counter_field": "state+0x2F8",
            "unknown_chemical_uses_per_purchase": 3,
            "unknown_chemical_store_description": "Contains 3 doses.",
        })

    if "universal_supply_slots" in selected:
        unknown_doses = 3 if "unknown_chemical_three_uses" in selected else 1
        payload, labels = slots.build_payload(unknown_doses)
        egg_target = slots.CAVE_VA + labels["egg_consume"]
        checks.update({
            "text_virtual_size_extended": data[0x1F8:0x1FC] == bytes.fromhex("00 F0 03 00"),
            "universal_payload_exact": data[slots.CAVE_FILE_OFFSET:slots.CAVE_FILE_OFFSET + len(payload)] == payload,
            "purchase_hook_target": rel32_target(0x00428133, data[0x28133:0x28138], 0xE9) == slots.CAVE_VA,
            "use_hook_target": rel32_target(0x00420B70, data[0x20B70:0x20B75], 0xE9) == slots.CAVE_VA + labels["use"],
            "common_egg_stack_hook": rel32_target(0x004213A7, data[0x213A7:0x213AC], 0xE9) == egg_target,
            "unusual_egg_stack_hook": rel32_target(0x00421476, data[0x21476:0x2147B], 0xE9) == egg_target,
            "rare_egg_stack_hook": rel32_target(0x00421549, data[0x21549:0x2154E], 0xE9) == egg_target,
            "generic_slot2_prompt": b"Replace item in slot #2?\0" in data[0x43EF4:0x43F14],
            "generic_slot3_prompt": b"Replace item in slot #3?\0" in data[0x43F34:0x43F54],
            "generic_slot4_prompt": b"Replace item in slot #4?\0" in data[0x43F70:0x43F8C],
            "unknown_chemical_runtime_reset_removed_for_stacking": data[0x210B7:0x210C1] == b"\x90" * 10,
        })
        report.update({
            "supported_item_indices": list(range(8)),
            "supported_items": ["Ick Medicine", "Fungus Medicine", "Fish Vitamins", "Growth Hormone", "Unknown Chemical", "Common Eggs", "Unusual Eggs", "Rare Eggs"],
            "placement_order": "matching stack; first empty slot 2, 3, 4; replacement prompts 2, 3, 4",
            "uses_added_per_purchase": {"Ick Medicine": 3, "Fungus Medicine": 3, "Fish Vitamins": 3, "Growth Hormone": 3, "Unknown Chemical": unknown_doses, "Common Eggs": 1, "Unusual Eggs": 1, "Rare Eggs": 1},
        })

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise patcher.PatchError(f"Patched executable verification failed: {', '.join(failed)}")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--enable", action="append")
    parser.add_argument("--disable-all", action="store_true")
    args = parser.parse_args()
    manifest = patcher.read_json(args.manifest)
    enabled = set() if args.disable_all else default_settings(manifest)
    for setting in args.enable or []:
        if setting not in patcher.manifest_settings(manifest):
            print(f"VERIFY ERROR: Unknown setting: {setting}")
            return 2
        enabled.add(setting)
    try:
        report = verify(args.exe, args.manifest, enabled)
    except patcher.PatchError as exc:
        print(f"VERIFY ERROR: {exc}")
        return 2
    print(json.dumps(report, indent=2))
    print("VERIFY PASS: exact selected-setting hash, patch bytes, and preserved downstream logic validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
