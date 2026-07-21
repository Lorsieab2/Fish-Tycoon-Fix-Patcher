#!/usr/bin/env python3
"""Validate every nonempty v1.2 setting combination against the private EXE."""

from __future__ import annotations

import argparse
import ctypes
from itertools import combinations
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile

import offline_fish_tycoon_patcher as patcher
import verify_patched_exe as verifier


def imagehlp_checksum(path: Path) -> tuple[int, int]:
    header = ctypes.c_ulong()
    computed = ctypes.c_ulong()
    result = ctypes.windll.imagehlp.MapFileAndCheckSumW(str(path), ctypes.byref(header), ctypes.byref(computed))
    if result != 0:
        raise RuntimeError(f"MapFileAndCheckSumW failed with code {result}: {path}")
    return header.value, computed.value


def loader_test(path: Path) -> None:
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = 0
    process = subprocess.Popen([str(path)], cwd=str(path.parent), startupinfo=startup,
                               creationflags=0x00000004 | 0x08000000)
    try:
        process.terminate()
        process.wait(timeout=10)
    finally:
        if process.poll() is None:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--skip-loader", action="store_true")
    args = parser.parse_args()
    manifest = patcher.read_json(args.manifest)
    patcher.validate_original_executable(args.original, manifest)
    setting_ids = list(patcher.manifest_settings(manifest))
    results = []
    with tempfile.TemporaryDirectory(prefix="fish-tycoon-v12-validate-") as temp:
        root = Path(temp)
        for count in range(1, len(setting_ids) + 1):
            for combo in combinations(setting_ids, count):
                enabled = set(combo)
                output, _ = patcher.apply_patch_bytes(args.original.read_bytes(), patcher.active_patch_records(manifest, enabled))
                exe = root / ("+".join(combo)) / "Fish Tycoon.exe"
                exe.parent.mkdir(parents=True)
                exe.write_bytes(output)
                report = verifier.verify(exe, args.manifest, enabled)
                header, computed = imagehlp_checksum(exe)
                if header != computed or header == 0:
                    raise RuntimeError(f"PE checksum mismatch for {combo}: header={header:#x}, computed={computed:#x}")
                if not args.skip_loader:
                    loader_test(exe)
                results.append({"settings": list(combo), "sha256": report["sha256"], "pe_checksum": f"0x{header:08X}", "loader": "skipped" if args.skip_loader else "CreateProcessW success"})
    print(json.dumps(results, indent=2))
    print(f"VALIDATION PASS: {len(results)} setting combinations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
