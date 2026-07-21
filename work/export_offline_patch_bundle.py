#!/usr/bin/env python3
"""Export the self-contained player-facing Fish Tycoon patcher folder."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil


LAUNCH_GUI = r'''@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%offline_fish_tycoon_patcher_gui.py"
) else (
  python "%SCRIPT_DIR%offline_fish_tycoon_patcher_gui.py"
)
'''

APPLY_PATCHER = r'''@echo off
setlocal
set "SCRIPT_DIR=%~dp0"
set /p "GAME_DIR=Enter the full path to the folder containing Fish Tycoon.exe: "
where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 "%SCRIPT_DIR%offline_fish_tycoon_patcher.py" apply --game-dir "%GAME_DIR%" --manifest "%SCRIPT_DIR%manifest.json"
) else (
  python "%SCRIPT_DIR%offline_fish_tycoon_patcher.py" apply --game-dir "%GAME_DIR%" --manifest "%SCRIPT_DIR%manifest.json"
)
pause
'''

HOW_TO_USE = r'''Fish Tycoon Fix Patcher - How to Use
========================================

ELI5 version:
This patcher checks your official classic Windows Fish Tycoon.exe and makes a
separate fixed copy of the complete game folder. It does not overwrite the
vanilla folder you select.

Check for updates:
https://github.com/Lorsieab2/Fish-Tycoon-Fix-Patcher/releases

1. Close Fish Tycoon and the trainer before patching.

2. Unzip this patcher package anywhere outside the game folder.

3. Run:
   Launch_GUI.bat

4. Select the vanilla game folder containing Fish Tycoon.exe.

5. Keep both fixes checked:
   - Crimson Comet 20% curing fix
   - Unknown Chemical: 3 uses

6. Optional but recommended: click Dry Run (Validate Only).
   This verifies the exact supported EXE and patch bytes without writing files.

7. Click Create Fixed Copy.

8. Run Fish Tycoon.exe from the new folder named:
   Fish Tycoon - Fixed

The patcher accepts only this exact original executable:
SHA-256: 9F15F13537AD0978D1E3AA2F94A64992FB7D968648BF265810087BDC88EDBDCD

The fixed executable has this exact SHA-256:
44CCC2EAA5633A88CDE03115C650F793E50391D48FFA707ADE44F284C808C49F

The fix performs one random roll from 0 through 99 for every eligible diseased
fish when a real body/fin (11,11) Crimson Comet is present. Results 0 through 19
enter the game's original disease-clear and cure-counter instructions: exactly
20 successful values out of 100.

The Unknown Chemical fix initializes its verified use counter to 3 instead of
1. The original after-use decrement and empty-at-zero behavior are unchanged.
Its English store description now ends with: Contains 3 doses.

The release does not contain Fish Tycoon.exe or any original game assets.

Trainer compatibility:
Fish Tycoon 1 Crimson Comet Test Trainer v1.4.0 and later accepts the exact
fixed executable hash shown above.

Have fun! -Lorsieab2 :)
'''


def export_bundle(repo: Path, output: Path) -> list[Path]:
    repo = repo.resolve()
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")
    output.mkdir(parents=True)
    sources = {
        repo / "work" / "offline_fish_tycoon_patcher.py": output / "offline_fish_tycoon_patcher.py",
        repo / "work" / "offline_fish_tycoon_patcher_gui.py": output / "offline_fish_tycoon_patcher_gui.py",
        repo / "work" / "verify_patched_exe.py": output / "verify_patched_exe.py",
        repo / "patches" / "fish-tycoon-fixes" / "manifest.json": output / "manifest.json",
        repo / "docs" / "Transparency Log.txt": output / "Transparency Log.txt",
        repo / "README.md": output / "README.txt",
        repo / "LICENSE": output / "LICENSE.txt",
    }
    written: list[Path] = []
    for source, destination in sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, destination)
        written.append(destination)
    for destination, text in (
        (output / "Launch_GUI.bat", LAUNCH_GUI),
        (output / "Apply_Patcher.bat", APPLY_PATCHER),
        (output / "How to Use.txt", HOW_TO_USE),
    ):
        destination.write_text(text.replace("\n", "\r\n"), encoding="utf-8")
        written.append(destination)
    forbidden = [path for path in output.rglob("*") if path.is_file() and path.suffix.lower() == ".exe"]
    if forbidden:
        raise RuntimeError(f"Release bundle unexpectedly contains executable(s): {forbidden}")
    return sorted(written)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parent.parent
    files = export_bundle(repo, args.output)
    print(f"files={len(files)}")
    for path in files:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
