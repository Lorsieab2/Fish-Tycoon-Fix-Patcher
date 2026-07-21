# Fish Tycoon Fix Patcher

Offline patcher for the official classic Windows version of *Fish Tycoon*.
Created with Codex AI in collaboration with Lorsieab2. The release contains no
game executable or original game assets.

## Included fixes

All three fixes are selected by default and can be enabled independently.

### Crimson Comet 20% curing fix

Replaces the unusable `Random(0)` result with one `0..99` roll. Values `0..19`
enter the game's existing disease-clear and Sick Fish Cured counter block. The
original exact body/fin `(11,11)` identity check remains unchanged.

### Unknown Chemical: 3 uses

Each purchase adds three uses instead of one. The patch removes the runtime
instruction that reset the counter to one on every use, allowing the existing
decrement and empty-at-zero logic to count down normally. The English store
description becomes `Contains 3 doses.`

### Universal supply slots 2-4

Slots 2, 3, and 4 accept exactly these store supplies:

- Ick Medicine
- Fungus Medicine
- Fish Vitamins
- Growth Hormone
- Unknown Chemical
- Common Eggs
- Unusual Eggs
- Rare Eggs

The game's normal localized `Buy this ...?` confirmation appears first. After
the player accepts, a purchase adds to a matching item stack. If none exists, it uses the
first empty slot in order 2, 3, 4. If all three are occupied, the player is
asked about replacing slot 2, then 3, then 4; declining all three cancels the
purchase. Medicines, vitamins, and Growth Hormone add 3 uses per purchase;
eggs add 1; Unknown Chemical adds 1 or 3 according to its separate checkbox.
Using a supported item from any of these physical slots routes it through the
game's original item handler, and egg stacks clear only after their final use.

## Safety and use

Download the newest ZIP from the [releases page](https://github.com/Lorsieab2/Fish-Tycoon-Fix-Patcher/releases),
extract it, close Fish Tycoon and the trainer, and run `Launch_GUI.bat`.

The patcher validates the exact original executable and every expected byte,
supports a no-write dry run, copies the complete game folder to a separate
`Fish Tycoon - Fixed` folder, creates a verified backup, writes apply/restore
logs, and computes the correct PE checksum for every setting combination. The
modded EXE retains the base game's embedded resource section and application
icon byte-for-byte. After installing the output, the patcher asks Windows
Explorer to refresh that EXE's cached icon.

## Supported executable

```text
Filename: Fish Tycoon.exe
Size:     385024 bytes
SHA-256:  9F15F13537AD0978D1E3AA2F94A64992FB7D968648BF265810087BDC88EDBDCD
PE:       x86 / PE32, timestamp 0x536BDE35, image base 0x00400000
```

The default all-fixes output is:

```text
SHA-256: CC498FE29D84F6486AB69CE8C02ADE67096BDE60670AAF740B9CC580C4B68C58
```

All seven nonempty setting-combination hashes are recorded in
`patches/fish-tycoon-fixes/manifest.json`. Fish Tycoon 1 Crimson Comet Test
Trainer v1.5.1 and later recognizes the v1.2.1 outputs.

## Development

Run tests from the repository root:

```powershell
python -m unittest discover -s work -p "test_*.py"
```

The `work` folder contains the patcher, GUI, deterministic x86 payload builder,
independent verifier, exporter, packager, and tests. Private reference files,
outputs, caches, archives, backups, and game files are excluded from Git.
