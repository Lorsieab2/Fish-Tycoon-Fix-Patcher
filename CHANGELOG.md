# Changelog

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
