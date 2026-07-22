#!/usr/bin/env python3
"""Build the deterministic x86 payload for universal supply slots 2-4."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct


IMAGE_BASE = 0x00400000
CAVE_FILE_OFFSET = 0x3F2A0
CAVE_VA = IMAGE_BASE + CAVE_FILE_OFFSET
PURCHASE_HOOK_VA = 0x00428133
USE_HOOK_VA = 0x00420B70


class X86:
    def __init__(self, base: int) -> None:
        self.base = base
        self.code = bytearray()
        self.labels: dict[str, int] = {}
        self.rel_fixups: list[tuple[int, str | int]] = []
        self.abs_fixups: list[tuple[int, str]] = []

    def emit(self, data: bytes | list[int]) -> None:
        self.code.extend(data)

    def label(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.code)

    def rel32(self, opcode: bytes, target: str | int) -> None:
        self.emit(opcode)
        position = len(self.code)
        self.emit(b"\0\0\0\0")
        self.rel_fixups.append((position, target))

    def abs32(self, prefix: bytes, label: str, addend: int = 0) -> None:
        self.emit(prefix)
        position = len(self.code)
        self.emit(struct.pack("<I", addend))
        self.abs_fixups.append((position, label))

    def align(self, boundary: int) -> None:
        while len(self.code) % boundary:
            self.code.append(0x90)

    def finish(self) -> bytes:
        for position, target in self.rel_fixups:
            target_va = self.base + self.labels[target] if isinstance(target, str) else target
            next_va = self.base + position + 4
            struct.pack_into("<i", self.code, position, target_va - next_va)
        for position, label in self.abs_fixups:
            current = struct.unpack_from("<I", self.code, position)[0]
            struct.pack_into("<I", self.code, position, self.base + self.labels[label] + current)
        return bytes(self.code)


def emit_prompt(code: X86, string_id: int, yes_label: str) -> None:
    code.emit([0x6A, 0x01])                         # push 1
    code.emit(b"\x68" + struct.pack("<I", string_id))  # push string id
    code.emit([0x8D, 0x4C, 0x24, 0x1C])           # lea ecx,[esp+1c] dialog
    code.rel32(b"\xE8", 0x004221A0)              # dialog constructor
    code.emit([0xC7,0x84,0x24,0x8C,0,0,0,1,0,0,0])
    code.emit([0x8B, 0x46, 0x20])                 # mov eax,[esi+20]
    code.emit([0x6A, 0x00, 0x50])                 # push 0; push parent
    code.emit([0x8D, 0x4C, 0x24, 0x1C])           # lea ecx,[esp+1c]
    code.rel32(b"\xE8", 0x00401D00)              # modal yes/no
    code.emit([0x8B, 0xD8])                       # mov ebx,eax
    code.emit([0xC7,0x84,0x24,0x8C,0,0,0,0xFF,0xFF,0xFF,0xFF])
    code.emit([0x8D, 0x4C, 0x24, 0x14])           # lea ecx,[esp+14]
    code.rel32(b"\xE8", 0x00422440)              # dialog destructor
    code.emit([0x85, 0xDB])                       # test ebx,ebx (0 = Yes)
    code.rel32(b"\x0F\x84", yes_label)


def build_payload(unknown_doses: int) -> tuple[bytes, dict[str, int]]:
    if unknown_doses not in (1, 3):
        raise ValueError("unknown_doses must be 1 or 3")
    code = X86(CAVE_VA)

    # Purchase hook, entered after original registration and affordability checks.
    code.label("purchase")
    code.emit([0x83, 0xFF, 0x07])                 # cmp edi,7
    code.rel32(b"\x0F\x87", "purchase_original")
    # Preserve the store's normal localized "Buy this ...?" confirmation for
    # every supported item before selecting, stacking, or replacing a slot.
    emit_prompt(code, 0xEC, "purchase_confirmed")
    code.rel32(b"\xE9", 0x00428225)              # player declined the purchase
    code.label("purchase_confirmed")
    code.emit([0x8B, 0x4E, 0x10])                 # reload state; dialog calls clobber ecx
    code.emit([0x83,0xB9,0xE0,0x02,0,0,0])       # occupied slot 2?
    code.rel32(b"\x0F\x84", "match_3")
    code.emit([0x39,0xB9,0xD4,0x02,0,0])         # same item in slot 2?
    code.rel32(b"\x0F\x84", "stack_2")
    code.label("match_3")
    code.emit([0x83,0xB9,0xFC,0x02,0,0,0])
    code.rel32(b"\x0F\x84", "match_4")
    code.emit([0x39,0xB9,0xF0,0x02,0,0])
    code.rel32(b"\x0F\x84", "stack_3")
    code.label("match_4")
    code.emit([0x83,0xB9,0x18,0x03,0,0,0])
    code.rel32(b"\x0F\x84", "find_empty")
    code.emit([0x39,0xB9,0x0C,0x03,0,0])
    code.rel32(b"\x0F\x84", "stack_4")

    code.label("find_empty")
    code.emit([0x83,0xB9,0xE0,0x02,0,0,0])       # slot 2 empty?
    code.rel32(b"\x0F\x84", "choose_2")
    code.emit([0x83,0xB9,0xFC,0x02,0,0,0])       # slot 3 empty?
    code.rel32(b"\x0F\x84", "choose_3")
    code.emit([0x83,0xB9,0x18,0x03,0,0,0])       # slot 4 empty?
    code.rel32(b"\x0F\x84", "choose_4")

    emit_prompt(code, 0xEF, "choose_2")
    emit_prompt(code, 0xEE, "choose_3")
    emit_prompt(code, 0xED, "choose_4")
    code.rel32(b"\xE9", 0x00428225)              # cancelled all replacements

    code.label("choose_2")
    code.emit(b"\xBB\x01\x00\x00\x00")
    code.rel32(b"\xE9", "purchase_new")
    code.label("choose_3")
    code.emit(b"\xBB\x02\x00\x00\x00")
    code.rel32(b"\xE9", "purchase_new")
    code.label("choose_4")
    code.emit(b"\xBB\x03\x00\x00\x00")
    code.rel32(b"\xE9", "purchase_new")

    code.label("stack_2")
    code.emit(b"\xBB\x01\x00\x00\x00")
    code.emit([0x8B,0x81,0xDC,0x02,0,0])
    code.rel32(b"\xE9", "purchase_stacked")
    code.label("stack_3")
    code.emit(b"\xBB\x02\x00\x00\x00")
    code.emit([0x8B,0x81,0xF8,0x02,0,0])
    code.rel32(b"\xE9", "purchase_stacked")
    code.label("stack_4")
    code.emit(b"\xBB\x03\x00\x00\x00")
    code.emit([0x8B,0x81,0x14,0x03,0,0])

    code.label("purchase_stacked")
    code.emit([0x89,0x44,0x24,0x10])              # save existing uses
    code.rel32(b"\xE9", "purchase_selected")

    code.label("purchase_new")
    code.emit([0xC7,0x44,0x24,0x10,0,0,0,0])     # replacement/new stack starts at zero

    code.label("purchase_selected")
    code.abs32(b"\x8B\x04\xFD", "item_table")  # mov eax,[edi*8+table]
    code.abs32(b"\x8B\x14\xFD", "item_table", 4)
    code.emit([0x52, 0x50, 0x57, 0x53, 0x8B, 0xCE])
    code.rel32(b"\xE8", 0x00427540)              # original purchase writer
    code.emit([0x8B,0x4E,0x10,0x6B,0xD3,0x1C])   # state; slot*28
    code.emit([0x8D,0x8C,0x11,0xC0,0x02,0,0])    # count field
    code.emit([0x8B,0x44,0x24,0x10])              # prior uses
    code.emit([0x83,0xFF,0x04])
    code.rel32(b"\x0F\x82", "add_three")
    code.rel32(b"\x0F\x84", "add_unknown")
    code.emit([0x83,0xC0,0x01])                   # each egg purchase adds one
    code.rel32(b"\xE9", "store_count")
    code.label("add_three")
    code.emit([0x83,0xC0,0x03])                   # medicines/vitamins/hormone
    code.rel32(b"\xE9", "store_count")
    code.label("add_unknown")
    code.emit([0x83,0xC0,unknown_doses])           # setting-specific package size
    code.label("store_count")
    code.emit([0x89,0x01])
    code.rel32(b"\xE9", 0x00428225)

    code.label("purchase_original")
    code.emit([0x83, 0xFF, 0x19])                 # displaced original range check
    code.rel32(b"\x0F\x87", 0x004281D6)
    code.rel32(b"\xE9", 0x0042813C)

    code.align(4)
    code.label("item_table")
    for icon, alternate in ((167,173),(168,174),(169,175),(122,123),
                            (170,176),(121,121),(171,171),(172,172)):
        code.emit(struct.pack("<II", icon, alternate))

    # Runtime use hook. If an item is outside its former category slot, swap its
    # complete 28-byte record into the original category slot, run the original
    # handler, then swap the modified record back.
    code.align(16)
    code.label("use")
    code.emit([0x53, 0x56, 0x57, 0x55])           # preserve ebx,esi,edi,ebp
    code.emit([0x8B, 0xF1])                       # esi=this
    code.emit([0x8B, 0x5E, 0x1C])                 # ebx=selected slot
    code.emit([0x83, 0xFB, 0x01])
    code.rel32(b"\x0F\x8C", "use_original")
    code.emit([0x83, 0xFB, 0x03])
    code.rel32(b"\x0F\x8F", "use_original")
    code.emit([0x8B, 0x46, 0x34])                 # eax=state
    code.emit([0x6B, 0xD3, 0x1C])                 # edx=slot*28
    code.emit([0x8B,0x94,0x10,0xB8,0x02,0,0])    # edx=item index
    code.emit([0x83, 0xFA, 0x01])
    code.rel32(b"\x0F\x8E", "category_1")
    code.emit([0x83, 0xFA, 0x04])
    code.rel32(b"\x0F\x8E", "category_2")
    code.emit([0x83, 0xFA, 0x07])
    code.rel32(b"\x0F\x8E", "category_3")
    code.rel32(b"\xE9", "use_original")

    code.label("category_1")
    code.emit(b"\xBF\x01\x00\x00\x00")
    code.rel32(b"\xE9", "category_ready")
    code.label("category_2")
    code.emit(b"\xBF\x02\x00\x00\x00")
    code.rel32(b"\xE9", "category_ready")
    code.label("category_3")
    code.emit(b"\xBF\x03\x00\x00\x00")

    code.label("category_ready")
    code.emit([0x3B, 0xDF])                       # cmp ebx,edi
    code.rel32(b"\x0F\x84", "use_original")
    code.rel32(b"\xE8", "swap_records")
    code.emit([0x89, 0x7E, 0x1C])                 # dispatch canonical category
    code.emit([0x8B, 0x44, 0x24, 0x18])           # original arg4
    code.emit([0x8B, 0x54, 0x24, 0x14])           # original arg3
    code.emit([0x50, 0x52, 0x8B, 0xCE])
    code.rel32(b"\xE8", "use_trampoline")
    code.rel32(b"\xE8", "swap_records")
    code.emit([0x89, 0x5E, 0x1C])                 # restore the physical selected slot
    code.emit([0x5D, 0x5F, 0x5E, 0x5B])
    code.emit([0xC2, 0x08, 0x00])

    code.label("use_original")
    code.emit([0x5D, 0x5F, 0x5E, 0x5B])
    code.rel32(b"\xE9", "use_trampoline")

    code.label("swap_records")
    code.emit([0x8B, 0x46, 0x34])
    code.emit([0x6B, 0xD3, 0x1C])
    code.emit([0x8D,0x94,0x10,0xB8,0x02,0,0])
    code.emit([0x6B, 0xEF, 0x1C])
    code.emit([0x8D,0xAC,0x28,0xB8,0x02,0,0])
    code.emit(b"\xB9\x07\x00\x00\x00")
    code.label("swap_loop")
    code.emit([0x8B,0x02, 0x87,0x45,0x00, 0x89,0x02,
               0x83,0xC2,0x04, 0x83,0xC5,0x04, 0x49])
    code.rel32(b"\x0F\x85", "swap_loop")
    code.emit([0xC3])

    code.label("use_trampoline")
    code.emit([0x83,0xEC,0x20,0x53,0x8B,0x5C,0x24,0x2C])
    code.rel32(b"\xE9", 0x00420B78)

    # Shared egg-stack consumption used by Common, Unusual, and Rare Eggs.
    code.align(16)
    code.label("egg_consume")
    code.emit([0x8B,0x56,0x34])
    code.emit([0x83,0xAA,0x14,0x03,0,0,0x01])     # --slot4 uses
    code.rel32(b"\x0F\x8F", "egg_consume_return")
    code.emit([0x33,0xC0])
    for offset in (0x30C,0x310,0x314,0x318,0x31C):
        code.emit(b"\x89\x82" + struct.pack("<I", offset))
    code.label("egg_consume_return")
    code.emit([0xC3])

    payload = code.finish()
    return payload, dict(code.labels)


def rel32_patch(source_va: int, target_va: int, total_length: int) -> bytes:
    result = b"\xE9" + struct.pack("<i", target_va - (source_va + 5))
    return result + b"\x90" * (total_length - len(result))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--unknown-doses", type=int, choices=(1, 3), default=1)
    args = parser.parse_args()
    payload, labels = build_payload(args.unknown_doses)
    report = {
        "cave_file_offset": f"0x{CAVE_FILE_OFFSET:X}",
        "cave_va": f"0x{CAVE_VA:08X}",
        "payload_length": len(payload),
        "purchase_hook": rel32_patch(PURCHASE_HOOK_VA, CAVE_VA, 9).hex(" ").upper(),
        "unknown_doses_per_purchase": args.unknown_doses,
        "use_hook": rel32_patch(USE_HOOK_VA, CAVE_VA + labels["use"], 8).hex(" ").upper(),
        "egg_common_hook": rel32_patch(0x004213A7, CAVE_VA + labels["egg_consume"], 42).hex(" ").upper(),
        "egg_unusual_hook": rel32_patch(0x00421476, CAVE_VA + labels["egg_consume"], 42).hex(" ").upper(),
        "egg_rare_hook": rel32_patch(0x00421549, CAVE_VA + labels["egg_consume"], 42).hex(" ").upper(),
        "payload": payload.hex(" ").upper(),
    }
    use_offset = labels["use"]
    report["use_va"] = f"0x{CAVE_VA + use_offset:08X}"
    print(json.dumps(report, indent=2) if args.json else f"payload_length={len(payload)} use_offset=0x{use_offset:X}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
