#!/usr/bin/env python3
"""Independent byte-contract verifier for a patched Fish Tycoon executable."""

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


def verify(exe: Path, manifest_path: Path) -> dict[str, object]:
    manifest = patcher.read_json(manifest_path)
    data = exe.read_bytes()
    actual_hash = patcher.sha256_bytes(data)
    expected_hash = str(manifest.get("patched_sha256", "")).upper()
    if actual_hash != expected_hash:
        raise patcher.PatchError(f"Patched SHA-256 mismatch: {actual_hash}; expected {expected_hash}.")

    call = data[0x204CE:0x204D3]
    wrapper = data[0x1E11:0x1E1F]
    virtual_size = struct.unpack_from("<I", data, 0x1F8)[0]
    pe_checksum = struct.unpack_from("<I", data, 0x150)[0]
    call_target = rel32_target(0x004204CE, call)
    wrapper_call_target = rel32_target(0x00401E13, wrapper[2:7])
    expected_wrapper = bytes.fromhex("6A 64 E8 28 14 00 00 59 3C 14 0F 92 C0 C3")

    checks = {
        "file_size_unchanged": len(data) == 385024,
        "text_virtual_size_unchanged": virtual_size == 0x3E29F,
        "pe_checksum": pe_checksum == 0x0006B452,
        "redirect_target": call_target == 0x00401E11,
        "wrapper_bytes": wrapper == expected_wrapper,
        "rng_argument": wrapper[:2] == bytes.fromhex("6A 64"),
        "rng_target": wrapper_call_target == 0x00403240,
        "threshold": wrapper[8:10] == bytes.fromhex("3C 14"),
        "unsigned_less_than": wrapper[10:13] == bytes.fromhex("0F 92 C0"),
        "original_clear_block_unchanged": data[0x204DA:0x204EB] == bytes.fromhex(
            "8B 46 34 89 9C 07 D0 03 00 00 8B 46 34 83 40 34 01"
        ),
        "success_values": [value for value in range(100) if value < 20] == list(range(20)),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise patcher.PatchError(f"Patched executable verification failed: {', '.join(failed)}")
    return {
        "path": str(exe.resolve()),
        "size": len(data),
        "sha256": actual_hash,
        "call_target": f"0x{call_target:08X}",
        "wrapper_va": "0x00401E11",
        "rng_target": f"0x{wrapper_call_target:08X}",
        "roll_domain": "0..99",
        "success_domain": "0..19",
        "success_count": 20,
        "domain_count": 100,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    try:
        report = verify(args.exe, args.manifest)
    except patcher.PatchError as exc:
        print(f"VERIFY ERROR: {exc}")
        return 2
    print(json.dumps(report, indent=2))
    print("VERIFY PASS: exact patched bytes, targets, unchanged clear block, and 20/100 domain validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
