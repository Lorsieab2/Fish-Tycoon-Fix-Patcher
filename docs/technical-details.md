# Fish Tycoon Fix Patcher v1.2.0: technical details

## Crimson Comet curing

At VA `0x004204CE`, the original program calls its exclusive-upper-bound RNG
helper with zero. The five-byte call is redirected to a 14-byte wrapper at
`0x00401E11`. The wrapper calls the same helper with 100 and returns true only
for unsigned values below 20. The original `(11,11)` scanner, disease clear,
and counter increment remain in place.

## Unknown Chemical count correction

The instruction at VA/file `0x004210B7`/`0x210B7` writes one to the active
chemical count while the item is used. Setting it to three would reset the
counter on every use. v1.2 replaces the complete ten-byte instruction with
NOPs, preserving the count established by the purchase path. Universal slots
add one per Unknown Chemical purchase when the three-use setting is off and
three when it is on. The original decrement at `0x00421305` remains unchanged.

## Universal slots and stacking

The purchase hook at `0x00428133` accepts only store indices `0..7`. It searches
occupied slot records 2, 3, 4 for the same item index, then searches for an
empty icon field in slot order, then presents generic replacement prompts.
The purchase writer remains `0x00427540`; the wrapper replaces its default count
with the previous stack count plus the item-specific purchase amount.

The use hook at `0x00420B70` temporarily swaps a complete 28-byte slot record
into the original category slot, calls the unmodified original handler through
a trampoline, swaps the records back, and restores the physical selected slot.
This retains the original item effects without duplicating them.

Common, Unusual, and Rare Egg clear blocks at `0x004213A7`, `0x00421476`, and
`0x00421549` call a shared routine that decrements slot 4's count and clears the
record only at zero. Other item cases are not added to the supported set.

The payload occupies verified zero padding beginning at file `0x3F2A0` / VA
`0x0043F2A0`. The first `.text` section VirtualSize is extended from `0x3E29F`
to `0x3F000`; raw size, file size, section layout, and SizeOfImage do not change.
English and German slot prompts are changed to generic item-replacement text.

The manifest stores exact expected/replacement bytes, all seven nonempty
setting hashes, and mutually exclusive PE checksum records. The patcher rejects
any executable identity or byte sequence that does not match.
