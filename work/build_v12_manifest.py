#!/usr/bin/env python3
"""Generate the exact v1.2 manifest and all seven patched hashes/checksums."""

from __future__ import annotations

from itertools import combinations
import json
from pathlib import Path
import struct

import build_universal_slots_patch as slots
import offline_fish_tycoon_patcher as patcher


ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "reference" / "private" / "user-supplied" / "Fish Tycoon.exe"
MANIFEST = ROOT / "patches" / "fish-tycoon-fixes" / "manifest.json"
CURE = "crimson_comet_20_percent_cure"
CHEMICAL = "unknown_chemical_three_uses"
UNIVERSAL = "universal_supply_slots"


def hx(data: bytes) -> str:
    return data.hex(" ").upper()


def record(identifier: str, offset: int, expected: bytes, replacement: bytes,
           requires: list[str], note: str, excludes: list[str] | None = None) -> dict[str, object]:
    value: dict[str, object] = {
        "id": identifier,
        "file_path": "Fish Tycoon.exe",
        "offset": f"0x{offset:X}",
        "expected": hx(expected),
        "replacement": hx(replacement),
        "requires": requires,
        "note": note,
    }
    if excludes:
        value["excludes"] = excludes
    return value


def padded(text: str, length: int) -> bytes:
    raw = text.encode("cp1252") + b"\0"
    if len(raw) > length:
        raise ValueError(f"String does not fit {length} bytes: {text}")
    return raw.ljust(length, b"\0")


def pe_checksum(data: bytes, checksum_offset: int = 0x150) -> int:
    work = bytearray(data)
    work[checksum_offset:checksum_offset + 4] = b"\0\0\0\0"
    total = 0
    for offset in range(0, len(work), 2):
        word = work[offset] | ((work[offset + 1] if offset + 1 < len(work) else 0) << 8)
        total = (total & 0xFFFF) + word + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (total + len(work)) & 0xFFFFFFFF


def resource_section(data: bytes) -> dict[str, object]:
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    section_count = struct.unpack_from("<H", data, pe_offset + 6)[0]
    optional_size = struct.unpack_from("<H", data, pe_offset + 20)[0]
    table = pe_offset + 24 + optional_size
    for index in range(section_count):
        header = struct.unpack_from("<8sIIIIIIHHI", data, table + index * 40)
        name = header[0].split(b"\0", 1)[0].decode("ascii")
        if name == ".rsrc":
            raw_size, raw_offset = header[3], header[4]
            raw = data[raw_offset:raw_offset + raw_size]
            return {"name": name, "offset": f"0x{raw_offset:X}", "size": raw_size, "sha256": patcher.sha256_bytes(raw)}
    raise ValueError("Original executable has no .rsrc section")


def active(records: list[dict[str, object]], enabled: set[str]) -> list[dict[str, object]]:
    return [r for r in records
            if all(x in enabled for x in r.get("requires", []))
            and not any(x in enabled for x in r.get("excludes", []))]


def main() -> int:
    original = ORIGINAL.read_bytes()
    payload1, labels1 = slots.build_payload(1)
    payload3, labels3 = slots.build_payload(3)
    assert len(payload1) == len(payload3)
    assert labels1 == labels3
    assert original[slots.CAVE_FILE_OFFSET:slots.CAVE_FILE_OFFSET + len(payload1)] == bytes(len(payload1))

    old_egg = {
        0x213A7: bytes.fromhex("89 A9 14 03 00 00 8B 56 34 89 AA 10 03 00 00 8B 46 34 89 A8 18 03 00 00 8B 4E 34 89 A9 1C 03 00 00 8B 56 34 89 AA 0C 03 00 00"),
        0x21476: bytes.fromhex("89 AA 14 03 00 00 8B 46 34 89 A8 10 03 00 00 8B 4E 34 89 A9 18 03 00 00 8B 56 34 89 AA 1C 03 00 00 8B 46 34 89 A8 0C 03 00 00"),
        0x21549: bytes.fromhex("89 AA 14 03 00 00 8B 46 34 89 A8 10 03 00 00 8B 4E 34 89 A9 18 03 00 00 8B 56 34 89 AA 1C 03 00 00 8B 46 34 89 A8 0C 03 00 00"),
    }
    egg_va = slots.CAVE_VA + labels1["egg_consume"]
    reset = bytes.fromhex("C7 80 F8 02 00 00 01 00 00 00")
    nops = bytes(0x90 for _ in range(10))
    records: list[dict[str, object]] = [
        record("redirect_crimson_comet_random_call", 0x204CE, bytes.fromhex("E8 6D 2D FE FF"), bytes.fromhex("E8 3E 19 FE FF"), [CURE], "Redirects the broken Random(0) call to the 20% wrapper."),
        record("install_crimson_comet_20_percent_wrapper", 0x1E11, bytes.fromhex("CC " * 14), bytes.fromhex("6A 64 E8 28 14 00 00 59 3C 14 0F 92 C0 C3"), [CURE], "Calls the original RNG once with 100 and succeeds for rolls 0..19."),
        record("unknown_chemical_remove_runtime_count_reset_chemical_only", 0x210B7, reset, nops, [CHEMICAL], "Preserves the purchased three-use count so each use decrements normally.", [UNIVERSAL]),
        record("unknown_chemical_remove_runtime_count_reset_slots_only", 0x210B7, reset, nops, [UNIVERSAL], "Preserves stacked one-dose purchases so each use decrements normally.", [CHEMICAL]),
        record("unknown_chemical_remove_runtime_count_reset_both", 0x210B7, reset, nops, [CHEMICAL, UNIVERSAL], "Preserves stacked three-dose purchases so each use decrements normally."),
        record("unknown_chemical_store_description_three_doses", 0x458C9, b"Contains one dose.", b"Contains 3 doses.\0", [CHEMICAL], "Changes the English store description to 'Contains 3 doses.'."),
        record("extend_text_virtual_size_for_slots_payload", 0x1F8, bytes.fromhex("9F E2 03 00"), bytes.fromhex("00 F0 03 00"), [UNIVERSAL], "Maps the existing zero-filled end of .text that contains the slot payload."),
        record("install_universal_slots_payload_unknown_one", slots.CAVE_FILE_OFFSET, bytes(len(payload1)), payload1, [UNIVERSAL], "Installs exact-item stacking and use routing; Unknown Chemical purchases add one use.", [CHEMICAL]),
        record("install_universal_slots_payload_unknown_three", slots.CAVE_FILE_OFFSET, bytes(len(payload3)), payload3, [UNIVERSAL, CHEMICAL], "Installs exact-item stacking and use routing; Unknown Chemical purchases add three uses."),
        record("redirect_store_purchase_for_universal_slots", 0x28133, bytes.fromhex("83 FF 19 0F 87 9A 00 00 00"), slots.rel32_patch(0x00428133, slots.CAVE_VA, 9), [UNIVERSAL], "Preserves the original Buy confirmation, then routes the exact eight supported items through matching-stack, empty-slot, and replacement logic."),
        record("redirect_item_use_for_universal_slots", 0x20B70, bytes.fromhex("83 EC 20 53 8B 5C 24 2C"), slots.rel32_patch(0x00420B70, slots.CAVE_VA + labels1["use"], 8), [UNIVERSAL], "Routes supported items through their original handler regardless of physical slot."),
    ]
    for name, offset, va in (("common", 0x213A7, 0x004213A7), ("unusual", 0x21476, 0x00421476), ("rare", 0x21549, 0x00421549)):
        records.append(record(f"stack_{name}_egg_uses", offset, old_egg[offset], slots.rel32_patch(va, egg_va, 42), [UNIVERSAL], f"Consumes one {name} egg use and clears the slot only when the stack reaches zero."))

    prompt_specs = (
        ("slot2_de", 0x43ED4, 32, "Artikel in Slot 2 ersetzen?"),
        ("slot2_en", 0x43EF4, 32, "Replace item in slot #2?"),
        ("slot3_de", 0x43F14, 32, "Artikel in Slot 3 ersetzen?"),
        ("slot3_en", 0x43F34, 32, "Replace item in slot #3?"),
        ("slot4_de", 0x43F54, 28, "Artikel in Slot 4 ersetzen?"),
        ("slot4_en", 0x43F70, 28, "Replace item in slot #4?"),
    )
    for name, offset, length, text in prompt_specs:
        records.append(record(f"generic_replacement_prompt_{name}", offset, original[offset:offset + length], padded(text, length), [UNIVERSAL], "Makes the replacement prompt accurate for every supported item."))

    settings = [
        {"id": CURE, "name": "Crimson Comet 20% curing fix", "description": "Rolls 0..99 once for each eligible diseased fish; 0..19 enters the original cure and counter block.", "category": "main", "default": True},
        {"id": CHEMICAL, "name": "Unknown Chemical: 3 uses", "description": "Each purchase adds three uses instead of one and the English store description says 'Contains 3 doses.'.", "category": "main", "default": True},
        {"id": UNIVERSAL, "name": "Universal supply slots 2-4", "description": "Keeps the normal Buy confirmation, then lets the eight supported medicines, chemicals, and egg types stack in any supply slot. Matching stack first, then empty slot 2-4, then replacement prompts.", "category": "main", "default": True},
    ]
    manifest: dict[str, object] = {
        "manifest_version": 3,
        "id": "fish-tycoon-pc-fixes-v4",
        "name": "Fish Tycoon Fix Patcher",
        "version": "v1.2.1",
        "description": "Repairs Crimson Comet curing, fixes Unknown Chemical uses, and lets the exact supported supplies stack in slots 2-4.",
        "patched_sha256": "",
        "patched_sha256_by_settings": {},
        "target": {"exe_name": "Fish Tycoon.exe", "size": len(original), "sha256": patcher.sha256_bytes(original), "pe_timestamp": "0x536BDE35", "machine": "0x014C", "optional_magic": "0x010B", "image_base": "0x00400000", "resource_section": resource_section(original)},
        "output": {"default_folder_name": "Fish Tycoon - Fixed", "exe_name": "Fish Tycoon.exe"},
        "settings": settings,
        "patches": records,
    }

    hashes: dict[str, str] = {}
    checksum_records: list[dict[str, object]] = []
    all_ids = [CURE, CHEMICAL, UNIVERSAL]
    for count in range(1, 4):
        for combo in combinations(all_ids, count):
            enabled = set(combo)
            output, _ = patcher.apply_patch_bytes(original, active(records, enabled))
            checksum = pe_checksum(output)
            checksum_bytes = struct.pack("<I", checksum)
            final = bytearray(output)
            final[0x150:0x154] = checksum_bytes
            key = patcher.settings_key(enabled)
            hashes[key] = patcher.sha256_bytes(bytes(final))
            checksum_records.append(record(
                "update_pe_checksum_" + "_".join(sorted(enabled)), 0x150,
                original[0x150:0x154], checksum_bytes, sorted(enabled),
                f"Sets the correct PE checksum 0x{checksum:08X} for this exact setting combination.",
                [item for item in all_ids if item not in enabled],
            ))
    manifest["patches"] = records + checksum_records
    manifest["patched_sha256_by_settings"] = hashes
    manifest["patched_sha256"] = hashes[patcher.settings_key(set(all_ids))]
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"manifest": str(MANIFEST), "hashes": hashes}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
