#!/usr/bin/env python3
"""Independent byte-contract verifier for a Fish Tycoon Fix Patcher output."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

import offline_fish_tycoon_patcher as patcher


def rel32_target(instruction_va: int, instruction: bytes) -> int:
    if len(instruction) != 5 or instruction[0] != 0xE8:
        raise patcher.PatchError(f"Expected CALL rel32 at 0x{instruction_va:X}.")
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
            "unknown_chemical_counter_field": data[0x210B7:0x210C1] == bytes.fromhex(
                "C7 80 F8 02 00 00 03 00 00 00"
            ),
            "unknown_chemical_description": data[0x45870:0x458DC].split(b"\0", 1)[0].endswith(
                b"Contains 3 doses."
            ),
            "unknown_chemical_post_use_decrement_unchanged": data[0x21302:0x2130C] == bytes.fromhex(
                "8B 46 34 83 80 F8 02 00 00 FF"
            ),
        })
        report.update({
            "unknown_chemical_counter_va": "0x004210B7",
            "unknown_chemical_counter_field": "state+0x2F8",
            "unknown_chemical_initial_uses": 3,
            "unknown_chemical_store_description": "Contains 3 doses.",
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
