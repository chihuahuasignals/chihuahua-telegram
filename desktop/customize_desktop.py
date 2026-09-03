#!/usr/bin/env python3
"""
customize_desktop.py — turns a clean Telegram Desktop (tdesktop) checkout into "Chihuahua Telegram".

Run by the GitHub Actions workflow:   python customize_desktop.py <path-to-tdesktop-checkout>

Settings (environment):
  APP_NAME       window/app name, also the data folder %APPDATA%\\<APP_NAME>   (default: Chihuahua Telegram)
  MAX_ACCOUNTS   accounts the app can hold                                    (default: 32)

api_id / api_hash are passed to CMake by the workflow (TDESKTOP_API_ID / TDESKTOP_API_HASH), not here.
Every edit is anchored on exact upstream text and the script aborts if an anchor is not found
exactly the expected number of times. (Build trigger: run 2.)
"""
import os
import shutil
import sys
import uuid
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "tdesktop").resolve()
HERE = Path(__file__).resolve().parent
ICONS = HERE.parent / "icons" / "desktop"

APP_NAME = os.environ.get("APP_NAME", "Chihuahua Telegram").strip()
MAX_ACCOUNTS = int(os.environ.get("MAX_ACCOUNTS", "32"))
APP_FILE = "".join(ch for ch in APP_NAME if ch.isalnum()) or "Chihuahua"
# Stable, unique AppUserModelID / installer id so Windows never confuses this app with the official one.
APP_ID = "{" + str(uuid.uuid5(uuid.NAMESPACE_DNS, "chihuahua-telegram.desktop." + APP_NAME)).upper() + "}"

errors = []


def fail(msg):
    errors.append(msg)
    print(f"  !! {msg}")


def edit(relpath, replacements):
    path = ROOT / relpath
    if not path.exists():
        fail(f"missing file {relpath}")
        return
    text = path.read_text(encoding="utf-8")
    for old, new, expected in replacements:
        n = text.count(old)
        if n != expected:
            fail(f"{relpath}: anchor found {n}x, expected {expected}x: {old.strip()[:70]!r}")
            continue
        text = text.replace(old, new)
    path.write_text(text, encoding="utf-8")
    print(f"  ok  {relpath}")


def main():
    if not (ROOT / "Telegram" / "CMakeLists.txt").exists():
        sys.exit(f"tdesktop checkout not found at {ROOT}")
    if not (2 <= MAX_ACCOUNTS <= 256):
        sys.exit("MAX_ACCOUNTS must be between 2 and 256")
    if not ICONS.is_dir():
        sys.exit(f"desktop icons missing at {ICONS}")
    print(f"Customizing Telegram Desktop at {ROOT}: name={APP_NAME!r} file={APP_FILE} accounts={MAX_ACCOUNTS} id={APP_ID}")

    # --- account limit (both constants; maxAccounts() = min(premium + kMaxAccounts, kPremiumMaxAccounts))
    edit("Telegram/SourceFiles/main/main_domain.h", [
        ("\tstatic constexpr auto kMaxAccounts = 3;\n\tstatic constexpr auto kPremiumMaxAccounts = 6;\n",
         f"\tstatic constexpr auto kMaxAccounts = {MAX_ACCOUNTS};\n\tstatic constexpr auto kPremiumMaxAccounts = {MAX_ACCOUNTS};\n", 1),
    ])
    # --- identity: name (also the %APPDATA% folder), exe/file name, Windows app id
    edit("Telegram/SourceFiles/core/version.h", [
        ('constexpr auto AppId = "{53F49750-6209-4FBF-9CA8-7A333C87D1ED}"_cs;',
         f'constexpr auto AppId = "{APP_ID}"_cs;', 1),
        ('constexpr auto AppName = "Telegram Desktop"_cs;', f'constexpr auto AppName = "{APP_NAME}"_cs;', 1),
        ('constexpr auto AppFile = "Telegram"_cs;', f'constexpr auto AppFile = "{APP_FILE}"_cs;', 1),
    ])
    # --- exe metadata (what Windows shows in Properties / Task Manager)
    edit("Telegram/Resources/winrc/Telegram.rc", [
        ('VALUE "CompanyName", "Telegram FZ-LLC"', f'VALUE "CompanyName", "{APP_NAME} (unofficial build)"', 1),
        ('VALUE "FileDescription", "Telegram Desktop"', f'VALUE "FileDescription", "{APP_NAME}"', 1),
        ('VALUE "ProductName", "Telegram Desktop"', f'VALUE "ProductName", "{APP_NAME}"', 1),
    ])
    # --- window title
    for rel in ("Telegram/SourceFiles/window/main_window.cpp",
                "Telegram/SourceFiles/window/window_saved_windows.cpp",
                "Telegram/SourceFiles/window/window_restore_shell.cpp"):
        edit(rel, [('u"Telegram"_q', f'u"{APP_NAME}"_q', 1)])
    # --- icons
    art = ROOT / "Telegram" / "Resources" / "art"
    copied = 0
    for f in ICONS.iterdir():
        if f.suffix in (".png", ".ico") and f.name != "preview.png":
            target = art / f.name
            if target.exists():
                shutil.copy(f, target)
                copied += 1
            else:
                print(f"  --  no upstream file for {f.name}, skipped")
    print(f"  ok  {copied} icon files replaced")

    if errors:
        print(f"\n{len(errors)} problem(s) — tdesktop no longer matches the anchors above.")
        sys.exit(1)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"### Desktop customization applied\n- Name: **{APP_NAME}**\n- Max accounts: **{MAX_ACCOUNTS}**\n- AppId: `{APP_ID}`\n")
    print("\nAll desktop customizations applied.")


if __name__ == "__main__":
    main()
