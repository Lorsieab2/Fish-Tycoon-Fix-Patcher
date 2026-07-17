# Fish Tycoon Bug Fix Patcher

Offline patcher for the official classic Windows version of *Fish Tycoon*.

Created with Codex AI in collaboration with Lorsieab2. This is a passion project
dedicated to improving the *Fish Tycoon* experience. No copyright infringement
is intended; please support the original game creators. :)

## Download

Download the newest patcher ZIP from the [official releases page](https://github.com/Lorsieab2/Fish-Tycoon-Bug-Fix-Patcher/releases).
Release ZIPs and patched game executables are intentionally not committed to the
source tree or included in releases.

The patcher creates a separate bug-fixed game folder by default and does not
overwrite the selected vanilla installation.

The fixed executable is supported by Fish Tycoon 1 Crimson Comet Test Trainer
v1.3.0 and later. Earlier trainer builds accept only the original executable.

## Shipped fix

### Crimson Comet 20% curing fix

The supported PC executable recognizes a diseased fish and the exact body/fin
`(11,11)` Crimson Comet, but its original branch calls the game's RNG helper
with `0`. That helper consumes a random number but can return only zero, and the
following zero test skips the disease-clear block.

The patch redirects only that broken call to a 14-byte wrapper placed in verified
compiler alignment padding between two functions. It updates only the PE checksum
field required for Windows loader validation; section layout is unchanged.
The wrapper:

1. calls the original exclusive-upper-bound RNG helper once with `100`, producing `0..99`;
2. returns success only when the result is below `20`; and
3. lets the game's original branch clear the disease and increment its original
   cure/status counter.

That gives exactly 20 successful values (`0..19`) out of 100. The existing
Crimson Comet identity check and the original disease-clear instructions remain
unchanged.

## What the patcher does

- Validates the exact supported `Fish Tycoon.exe` before changing anything.
- Supports dry-run validation with no writes.
- Copies the selected vanilla game folder to a separate bug-fixed folder.
- Applies only manifest-declared byte patches after checking every original byte.
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

The exact v1.0.0 patched executable hash is:

```text
33C8C9469E8E9F7DD460C4A9B9A3A897D2A9505C1E2627988046D8CED097AD9B
```

## Source layout

- `work/offline_fish_tycoon_patcher.py` - command-line validation, apply, backup,
  and restore engine.
- `work/offline_fish_tycoon_patcher_gui.py` - Tkinter GUI.
- `work/verify_patched_exe.py` - independent patched-byte and probability-domain
  verifier.
- `work/export_offline_patch_bundle.py` - release-folder exporter.
- `work/package_patcher_zip.py` - deterministic-layout ZIP packager.
- `work/test_*.py` - source and GUI contract tests.
- `patches/crimson-comet-20-percent/manifest.json` - transparent patch manifest.
- `docs/technical-details.md` - exact instruction and PE changes.
- `docs/Transparency Log.txt` - implementation and verification disclosure.

## Development

The repository is self-contained and contains no original game executable or
assets. Build outputs, patched executables, caches, backups, and archives remain
outside Git.

Run the tests from the repository root:

```powershell
python -m unittest work.test_offline_fish_tycoon_patcher work.test_offline_fish_tycoon_patcher_gui
```

Run a source-layout dry run:

```powershell
python work\offline_fish_tycoon_patcher.py apply `
  --game-dir "C:\Path\To\Fish Tycoon" `
  --manifest patches\crimson-comet-20-percent\manifest.json `
  --dry-run
```
