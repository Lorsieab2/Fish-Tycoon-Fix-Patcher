# Fish Tycoon Fix Patcher

Offline patcher for the official classic Windows version of *Fish Tycoon*.

Created with Codex AI in collaboration with Lorsieab2. This is a passion project
dedicated to improving the *Fish Tycoon* experience. No copyright infringement
is intended; please support the original game creators. :)

## Download

Download the newest patcher ZIP from the [official releases page](https://github.com/Lorsieab2/Fish-Tycoon-Fix-Patcher/releases).
The release contains no original or patched game executable and no original game
assets.

The patcher creates a separate `Fish Tycoon - Fixed` folder by default. It does
not overwrite the vanilla installation you select.

## Included fixes

Both fixes are selected by default and can be enabled independently.

### Crimson Comet 20% curing fix

The supported PC executable recognizes a diseased fish and the exact body/fin
`(11,11)` Crimson Comet, but its original branch calls the game's RNG helper
with `0`. The helper can return only zero, so the following zero test always
skips the existing disease-clear and cure-counter instructions.

The patch redirects that call to a 14-byte wrapper in verified compiler alignment
padding. The wrapper calls the original RNG helper once with `100`, producing
`0..99`, and reports success for `0..19`. The game's original Crimson Comet
identity test, disease clear, and cure-counter increment remain unchanged.

### Unknown Chemical: 3 uses

The patch changes the Unknown Chemical's verified use-counter initializer from
`1` to `3`. Its original after-use decrement and empty-at-zero behavior remain
unchanged. The English store description is changed from `Contains one dose.`
to `Contains 3 doses.`

## What the patcher does

- Validates the exact supported `Fish Tycoon.exe` before changing anything.
- Supports dry-run validation with no writes.
- Copies the complete selected game folder to a separate fixed folder.
- Applies only manifest-declared changes after checking every original byte.
- Recomputes the PE checksum for each selected fix combination.
- Creates a timestamped backup and machine-readable apply/restore logs.
- Supports restoring the output executable from its verified backup.
- Uses offline file patching; it does not inject into a running process.

After extracting a release, close Fish Tycoon and run `Launch_GUI.bat`. The
bundle also contains `How to Use.txt`.

## Supported executable

```text
Filename: Fish Tycoon.exe
Size:     385024 bytes
SHA-256:  9F15F13537AD0978D1E3AA2F94A64992FB7D968648BF265810087BDC88EDBDCD
PE:       x86 / PE32, timestamp 0x536BDE35, image base 0x00400000
```

Exact resulting hashes:

| Selected fixes | SHA-256 |
|---|---|
| Crimson Comet only | `33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B` |
| Unknown Chemical only | `7A78B09F0509BDFFC191FFB9637FA41F8E8FEC73A10A524A6B017F3E42E88983` |
| Both fixes (default) | `44CCC2EAA5633A88CDE03115C650F793E50391D48FFA707ADE44F284C808C49F` |

Fish Tycoon 1 Crimson Comet Test Trainer v1.4.0 and later supports the original
executable and all three patched variants listed above.

## Source layout

- `work/offline_fish_tycoon_patcher.py` - validation, apply, backup, and restore.
- `work/offline_fish_tycoon_patcher_gui.py` - Tkinter GUI.
- `work/verify_patched_exe.py` - independent patched-byte verifier.
- `work/export_offline_patch_bundle.py` - release-folder exporter.
- `work/package_patcher_zip.py` - deterministic-layout ZIP packager.
- `work/test_*.py` - source and GUI contract tests.
- `patches/fish-tycoon-fixes/manifest.json` - transparent patch manifest.
- `docs/technical-details.md` - exact instruction and PE changes.
- `docs/Transparency Log.txt` - implementation and verification disclosure.

## Development

The repository is self-contained and contains no game executable or assets.
Outputs, caches, backups, archives, and private reference files remain outside
Git.

Run all tests from the repository root:

```powershell
python -m unittest discover -s work -p "test_*.py"
```

Run a source-layout dry run:

```powershell
python work\offline_fish_tycoon_patcher.py apply `
  --game-dir "C:\Path\To\Fish Tycoon" `
  --manifest patches\fish-tycoon-fixes\manifest.json `
  --dry-run
```
