# Crimson Comet 20% cure fix: technical details

## Scope

This patch changes only the broken random call in the existing Crimson Comet
disease branch. It does not replace the body/fin presence scanner, discovery
logic, naming, sparkle rendering, breeding, egg generation, disease values,
treatment items, health, aging, or the original disease-clear instructions.

## Original PC branch

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

`sub_403240(0)` calls the CRT `rand()` but returns the remainder for a range
whose only possible result is zero. The final `test` therefore always takes the
skip branch.

## Patched flow

The five-byte call at VA `0x004204CE` / file offset `0x204CE` is redirected to a
14-byte wrapper at VA `0x00401E11` / file offset `0x1E11`:

```asm
00401E11  push 100
00401E13  call 00403240       ; one original RNG call, returns 0..99
00401E18  pop  ecx            ; discard cdecl argument; ECX is caller-clobbered
00401E19  cmp  al, 20         ; EAX is already limited to 0..99
00401E1B  setb al             ; 1 only for unsigned values 0..19
00401E1E  ret
```

The original `test eax,eax` and `jz` remain in place. A wrapper return of `1`
falls through into the original clear/counter block; `0` skips it.

## Probability contract

| Roll | Count | Result |
|---|---:|---|
| `0..19` | 20 | enter original clear block |
| `20..99` | 80 | skip clear block |

The domain contains 100 equally selected values under the game's original RNG
helper, so the success domain is exactly 20/100 = 20%.

## PE placement

The wrapper occupies 14 bytes of an existing 15-byte `INT3` alignment gap at
`0x00401E11..0x00401E1F`, between the tail jump ending `sub_401DF0` and the next
function at `0x00401E20`. File size, `.text` VirtualSize and RawSize, section
permissions, image base, timestamp, imports, and section layout remain unchanged.
The existing PE checksum is recomputed for the final bytes so Windows accepts
the modified image.

## Exact byte records

| File offset | Original | Replacement |
|---:|---|---|
| `0x204CE` | `E8 6D 2D FE FF` | `E8 3E 19 FE FF` |
| `0x1E11` | 14 `CC` bytes | `6A 64 E8 28 14 00 00 59 3C 14 0F 92 C0 C3` |
| `0x150` | `B0 09 06 00` (`0x000609B0`) | `52 B4 06 00` (`0x0006B452`) |

The patcher refuses the operation if the file identity or any original byte does
not match exactly.
