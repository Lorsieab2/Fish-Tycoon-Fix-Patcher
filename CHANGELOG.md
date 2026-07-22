# Changelog

## v1.2.4 - 2026-07-21

- Fixed the confirmed Common, Unusual, and Rare Egg use crash. Each egg hook
  now calls the shared decrement routine and then jumps to its exact original
  hatch continuation; no `ret` executes without a matching `call`.
- Restored the original item handler's verified `ret 8` convention and retains
  its completed-action selected-slot value instead of reselecting the slot.
- The GUI now mirrors the VF2 patcher by remembering and auto-populating the
  vanilla and modded paths and showing clickable completion-path links.
- Excludes `Fish Tycoon - Copy.exe` from the generated modded game folder.

## v1.2.3 - 2026-07-21

- Attempted to address supported-item crashes from non-original slots. Live
  reproduction later proved the egg path still crashed and dump analysis showed
  that the original item-use function actually uses `ret 8`.

## v1.2.2 - 2026-07-21

- Fixed a crash after accepting `Buy this Item?` when all supply slots were
  occupied by reloading the game-state pointer after the dialog closes.

## v1.2.1 - 2026-07-21

- Restored the original localized `Buy this ...?` confirmation before every
  supported medicine, chemical, or egg purchase.
- Kept stacking, empty-slot selection, and replacement prompts after Yes.

## v1.2.0 - 2026-07-21

- Added exact eight-item support for supply slots 2-4.
- Added matching-item stacking before empty-slot or replacement selection.
- Added stacked egg consumption for Common, Unusual, and Rare Eggs.
- Made Unknown Chemical stack by one or three uses according to its checkbox.
- Corrected the Unknown Chemical fix by removing its per-use count reset.
- Added generic English and German replacement prompts.
- Added exact hashes and PE checksums for all seven nonempty combinations.

## v1.1.0 - 2026-07-21

- Renamed the product to Fish Tycoon Fix Patcher.
- Added an optional Unknown Chemical three-use patch.
- Updated the English store description to match the three uses.
- Added exact hashes and PE checksums for all selectable combinations.

## v1.0.0 - 2026-07-17

- First public release with the Crimson Comet 20% curing fix.
