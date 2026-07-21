# Fish Tycoon Fix Patcher: technical details

## Crimson Comet 20% curing fix

### Original PC branch

The supported executable contains this sequence:

```asm
004204B6  cmp  dword ptr [edi+edx+3D0h], ebx ; disease/status != 0
004204BD  jz   004204EB
004204BF  push ebp                            ; tank
004204C0  push 2                              ; selector 2 = body/fin (11,11)
004204C2  mov  ecx, esi
004204C4  call 0041DE90                       ; tank-wide pair scanner
004204C9  test al, al
004204CB  jz   004204EB
004204CD  push ebx                            ; ebx is zero
004204CE  call 00403240                       ; RNG helper called with 0
004204D3  add  esp, 4
004204D6  test eax, eax
004204D8  jz   004204EB
004204DA  mov  eax, [esi+34h]
004204DD  mov  [edi+eax+3D0h], ebx            ; clear disease/status
004204E4  mov  eax, [esi+34h]
004204E7  add  dword ptr [eax+34h], 1         ; original cure counter
```

`sub_403240(0)` consumes a CRT `rand()` value but returns a remainder whose only
possible value is zero. The final test therefore always takes the skip branch.

### Patched flow

The five-byte call at VA `0x004204CE` / file offset `0x204CE` is redirected to a
14-byte wrapper at VA `0x00401E11` / file offset `0x1E11`:

```asm
00401E11  push 100
00401E13  call 00403240       ; one original RNG call, returns 0..99
00401E18  pop  ecx            ; discard cdecl argument
00401E19  cmp  al, 20
00401E1B  setb al             ; 1 only for unsigned values 0..19
00401E1E  ret
```

The original `test eax,eax`, conditional jump, identity test, disease clear,
and cure-counter increment remain in place. The success domain is exactly 20
values (`0..19`) out of 100 (`0..99`).

The wrapper occupies 14 bytes of an existing 15-byte `INT3` alignment gap at
`0x00401E11..0x00401E1F`. File size and PE section layout are unchanged.

| File offset | Original | Replacement |
|---:|---|---|
| `0x204CE` | `E8 6D 2D FE FF` | `E8 3E 19 FE FF` |
| `0x1E11` | 14 `CC` bytes | `6A 64 E8 28 14 00 00 59 3C 14 0F 92 C0 C3` |

## Unknown Chemical: 3 uses

The Unknown Chemical purchase branch initializes its use counter at
`state+0x2F8`. The original full instruction at VA `0x004210B7` / file offset
`0x210B7` is:

```asm
004210B7  mov dword ptr [eax+2F8h], 1
```

The patch changes only the immediate value from `1` to `3`:

| File offset | Original | Replacement |
|---:|---|---|
| `0x210B7` | `C7 80 F8 02 00 00 01 00 00 00` | `C7 80 F8 02 00 00 03 00 00 00` |

The original post-use decrement at VA `0x00421305` and the original counter
test/empty behavior remain unchanged. The purchase itself flows through that
existing decrement path, so initializing the counter to three gives three total
uses under the game's original behavior.

The unique English store-description substring at file offset `0x458C9` is
replaced with an equal-size, null-terminated string:

| Original | Replacement |
|---|---|
| `Contains one dose.` | `Contains 3 doses.\0` |

This release changes the English description only. It does not claim to alter
the separate German localization text.

## PE checksums and exact hashes

The patcher uses mutually exclusive manifest records to write the correct
recomputed PE checksum for each selected combination. No section layout changes.

| Selected fixes | PE checksum | SHA-256 |
|---|---:|---|
| Crimson Comet only | `0x0006B452` | `33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B` |
| Unknown Chemical only | `0x0006CB53` | `7A78B09F0509BDFFC191FFB9637FA41F8E8FEC73A10A524A6B017F3E42E88983` |
| Both fixes | `0x000675F6` | `44CCC2EAA5633A88CDE03115C650F793E50391D48FFA707ADE44F284C808C49F` |

The patcher refuses an operation unless the full original file identity and
every selected patch record's original bytes match exactly.
