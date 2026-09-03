#!/usr/bin/env python3
"""
patch_prepare.py — small fix to tdesktop's library recipe (Telegram/build/prepare/prepare.py)
before win.bat runs.   Usage: python patch_prepare.py <path-to-tdesktop-checkout>

The Release part of the "breakpad" stage also builds dump_syms, a tool that publishes crash-report
symbols. It needs the ATL headers (atlbase.h), which GitHub's Windows runners do not ship for the
pinned MSVC toolset, so the stage fails. Crash reports are disabled in this build, so dump_syms is
simply dropped. Telegram's own CI never sees this because it passes skip-release to win.bat.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1] if len(sys.argv) > 1 else "tdesktop").resolve()
path = root / "Telegram" / "build" / "prepare" / "prepare.py"
src = path.read_text(encoding="utf-8")

# Exactly as written inside prepare.py's triple-quoted stage string (backslashes are doubled there).
block = (
    "    cd tools\\\\windows\\\\dump_syms\n"
    "    gyp dump_syms.gyp --format=msvs\n"
    "    msbuild -m dump_syms.vcxproj /property:Configuration=Release /property:Platform=\"x64\" %ToolsetProp%\n"
)
n = src.count(block)
if n != 1:
    sys.exit(f"prepare.py: breakpad dump_syms block found {n}x, expected 1x — tdesktop changed, check patch_prepare.py")
path.write_text(src.replace(block, ""), encoding="utf-8")
print("prepare.py: breakpad dump_syms (needs ATL) removed from the Release stage")
