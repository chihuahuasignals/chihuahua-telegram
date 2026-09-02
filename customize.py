#!/usr/bin/env python3
"""
customize.py — turns a clean Telegram-Android checkout into "Chihuahua Telegram".

Run by the GitHub Actions workflow:   python3 customize.py <path-to-telegram-checkout>

Settings come from environment variables (the workflow loads config.env and the
repository secrets):

  APP_NAME           launcher label                       (default: Chihuahua Telegram)
  APP_PACKAGE        Android application id               (default: com.chihuahua.messenger)
  MAX_ACCOUNTS       accounts the app can hold            (default: 32)
  BUILD_ABI          arm64-v8a  |  all                    (default: arm64-v8a)
  GRADLE_HEAP        JVM heap for Gradle, e.g. 8g         (default: 8g)
  TG_API_ID          your api_id   from my.telegram.org   (required, secret)
  TG_API_HASH        your api_hash from my.telegram.org   (required, secret)
  KEYSTORE_PASSWORD  password of the signing keystore     (required, secret)
  KEYSTORE_ALIAS     key alias inside the keystore        (default: chihuahua)

Every edit is anchored on an exact piece of upstream text and the script aborts
if an anchor is not found exactly the expected number of times — so if Telegram
changes its code, the build fails loudly instead of producing a half-patched app.
"""
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "telegram").resolve()
HERE = Path(__file__).resolve().parent
ICONS = HERE / "icons"

APP_NAME = os.environ.get("APP_NAME", "Chihuahua Telegram").strip()
APP_PACKAGE = os.environ.get("APP_PACKAGE", "com.chihuahua.messenger").strip()
MAX_ACCOUNTS = int(os.environ.get("MAX_ACCOUNTS", "32"))
BUILD_ABI = os.environ.get("BUILD_ABI", "arm64-v8a").strip()
GRADLE_HEAP = os.environ.get("GRADLE_HEAP", "8g").strip()
TG_API_ID = os.environ.get("TG_API_ID", "").strip()
TG_API_HASH = os.environ.get("TG_API_HASH", "").strip()
KEYSTORE_PASSWORD = os.environ.get("KEYSTORE_PASSWORD", "").strip()
KEYSTORE_ALIAS = os.environ.get("KEYSTORE_ALIAS", "chihuahua").strip()

DENSITIES = ["mdpi", "hdpi", "xhdpi", "xxhdpi", "xxxhdpi"]
ICON_BG = "#F4A261"

errors = []


def fail(msg):
    errors.append(msg)
    print(f"  !! {msg}")


def check_inputs():
    if not ROOT.is_dir() or not (ROOT / "gradle.properties").exists():
        sys.exit(f"Telegram checkout not found at {ROOT}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+", APP_PACKAGE):
        sys.exit(f"APP_PACKAGE '{APP_PACKAGE}' is not a valid Android package name")
    if not (2 <= MAX_ACCOUNTS <= 256):
        sys.exit("MAX_ACCOUNTS must be between 2 and 256")
    if not TG_API_ID.isdigit():
        sys.exit("TG_API_ID secret is missing or not a number — add it in GitHub → Settings → Secrets → Actions")
    if not re.fullmatch(r"[0-9a-f]{32}", TG_API_HASH):
        sys.exit("TG_API_HASH secret is missing or not a 32-char hex string — add it in GitHub → Settings → Secrets → Actions")
    if not KEYSTORE_PASSWORD:
        sys.exit("KEYSTORE_PASSWORD secret is missing — add it in GitHub → Settings → Secrets → Actions")
    if BUILD_ABI not in ("arm64-v8a", "all"):
        sys.exit("BUILD_ABI must be arm64-v8a or all")
    if not ICONS.is_dir():
        sys.exit(f"icons folder missing at {ICONS}")


def edit(relpath, replacements):
    """replacements: list of (old, new, expected_count). Applies in order, verifies counts."""
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


def xml_escape(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;").replace("'", "\\'"))


def patch_gradle_properties():
    edit("gradle.properties", [
        ("APP_PACKAGE=org.telegram.messenger\n", f"APP_PACKAGE={APP_PACKAGE}\n", 1),
        ("RELEASE_KEY_PASSWORD=android\n", f"RELEASE_KEY_PASSWORD={KEYSTORE_PASSWORD}\n", 1),
        ("RELEASE_KEY_ALIAS=androidkey\n", f"RELEASE_KEY_ALIAS={KEYSTORE_ALIAS}\n", 1),
        ("RELEASE_STORE_PASSWORD=android\n", f"RELEASE_STORE_PASSWORD={KEYSTORE_PASSWORD}\n", 1),
        ("org.gradle.jvmargs=-Xmx8g -XX:MaxMetaspaceSize=1g\n",
         f"org.gradle.jvmargs=-Xmx{GRADLE_HEAP} -XX:MaxMetaspaceSize=1g\n", 1),
    ])


def patch_account_limit():
    edit("TMessagesProj/src/main/java/org/telegram/messenger/UserConfig.java", [
        ("public final static int MAX_ACCOUNT_DEFAULT_COUNT = 3;",
         f"public final static int MAX_ACCOUNT_DEFAULT_COUNT = {MAX_ACCOUNTS};", 1),
        ("public final static int MAX_ACCOUNT_COUNT = 4;",
         f"public final static int MAX_ACCOUNT_COUNT = {MAX_ACCOUNTS};", 1),
        ("return hasPremiumOnAccounts() ? 5 : 3;",
         "return MAX_ACCOUNT_COUNT;", 1),
    ])


def patch_build_vars():
    edit("TMessagesProj/src/main/java/org/telegram/messenger/BuildVars.java", [
        ("public static int APP_ID = 4;", f"public static int APP_ID = {TG_API_ID};", 1),
        ('public static String APP_HASH = "014b35b6184100b085b0d0572f9b5103";',
         f'public static String APP_HASH = "{TG_API_HASH}";', 1),
        ('public static String SAFETYNET_KEY = "AIzaSyDqt8P-7F7CPCseMkOiVRgb1LY8RN1bvH8";',
         'public static String SAFETYNET_KEY = "";', 1),
        ("public static boolean SUPPORTS_PASSKEYS = true;",
         "public static boolean SUPPORTS_PASSKEYS = false;", 1),
    ])


def patch_app_name():
    edit("TMessagesProj/src/main/res/values/strings.xml", [
        ('<string name="AppName">Telegram</string>',
         f'<string name="AppName">{xml_escape(APP_NAME)}</string>', 1),
        ('<string name="AppNameBeta">Telegram Beta</string>',
         f'<string name="AppNameBeta">{xml_escape(APP_NAME)} Beta</string>', 1),
    ])


def patch_abis():
    if BUILD_ABI == "all":
        print("  --  building all ABIs (slow)")
        return
    edit("TMessagesProj_App/build.gradle", [
        ('abiFilters "armeabi-v7a", "arm64-v8a", "x86", "x86_64"',
         f'abiFilters "{BUILD_ABI}"', 3),
    ])
    # The library module compiles the native code; without a filter it builds all four ABIs.
    edit("TMessagesProj/build.gradle", [
        ("    defaultConfig {\n        minSdkVersion 21\n        targetSdkVersion 36\n",
         "    defaultConfig {\n        minSdkVersion 21\n        targetSdkVersion 36\n"
         f'        ndk {{ abiFilters "{BUILD_ABI}" }}\n', 1),
    ])


def patch_google_services():
    # The google-services Gradle plugin refuses to build unless the JSON lists our package.
    # Push notifications through Firebase will not work with these placeholder entries
    # (the app falls back to its own background connection); see README for the fix.
    for rel in ("TMessagesProj/google-services.json", "TMessagesProj_App/google-services.json"):
        path = ROOT / rel
        if not path.exists():
            fail(f"missing file {rel}")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        clients = data.get("client", [])
        if not clients:
            fail(f"{rel}: no client entries")
            continue
        existing = {c["client_info"]["android_client_info"]["package_name"] for c in clients}
        for pkg in (APP_PACKAGE, APP_PACKAGE + ".beta", APP_PACKAGE + ".web"):
            if pkg in existing:
                continue
            new = json.loads(json.dumps(clients[0]))
            new["client_info"]["android_client_info"]["package_name"] = pkg
            clients.append(new)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"  ok  {rel}")


def patch_account_type():
    """Give the app its own Android account type / contact mime types so it can live
    next to the official app instead of fighting it for 'org.telegram.messenger'."""
    old_mime = "vnd.org.telegram.messenger.android"
    new_mime = f"vnd.{APP_PACKAGE}.android"
    edit("TMessagesProj/src/main/res/xml/auth.xml", [
        ('android:accountType="org.telegram.messenger"', f'android:accountType="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/sync_contacts.xml", [
        ('android:accountType="org.telegram.messenger"', f'android:accountType="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/auth_menu.xml", [
        ('android:targetPackage="org.telegram.messenger"', f'android:targetPackage="{APP_PACKAGE}"', 1),
    ])
    edit("TMessagesProj/src/main/res/xml/contacts.xml", [(old_mime, new_mime, 3)])
    edit("TMessagesProj/src/main/AndroidManifest.xml", [(old_mime, new_mime, 3)])
    edit("TMessagesProj/src/main/java/org/telegram/ui/LaunchActivity.java", [(old_mime, new_mime, 2)])
    edit("TMessagesProj/src/main/java/org/telegram/messenger/ContactsController.java", [
        (old_mime, new_mime, 3),
        ('"org.telegram.messenger"', 'ApplicationLoader.applicationContext.getPackageName()', 5),
    ])


def install_icons():
    res = ROOT / "TMessagesProj/src/main/res"
    for d in DENSITIES:
        mip = res / f"mipmap-{d}"
        if not mip.is_dir():
            fail(f"missing {mip}")
            continue
        shutil.copy(ICONS / f"foreground-{d}.png", mip / "icon_foreground.png")
        shutil.copy(ICONS / f"foreground-{d}.png", mip / "icon_foreground_round.png")
        shutil.copy(ICONS / f"launcher-{d}.png", mip / "ic_launcher.png")
        shutil.copy(ICONS / f"launcher_round-{d}.png", mip / "ic_launcher_round.png")
        dr = res / f"drawable-{d}" / "ic_launcher_dr.webp"
        if dr.exists():
            shutil.copy(ICONS / f"dr-{d}.webp", dr)
    solid = ('<?xml version="1.0" encoding="utf-8"?>\n'
             '<shape xmlns:android="http://schemas.android.com/apk/res/android" android:shape="rectangle">\n'
             f'    <solid android:color="{ICON_BG}" />\n'
             '</shape>\n')
    for name in ("icon_background.xml", "icon_background_round.xml"):
        p = res / "drawable" / name
        if not p.exists():
            fail(f"missing {p}")
            continue
        p.write_text(solid, encoding="utf-8")
    # Drop the monochrome (themed-icon) layer, which is Telegram's paper plane.
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        edit(f"TMessagesProj/src/main/res/mipmap-anydpi-v26/{name}", [
            ('    <monochrome android:drawable="@drawable/icon_plane" />\n', "", 1),
        ])
    print("  ok  launcher icons installed")


def write_summary():
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = [
        "### Customization applied",
        f"- App name: **{APP_NAME}**",
        f"- Package: `{APP_PACKAGE}`",
        f"- Max accounts: **{MAX_ACCOUNTS}**",
        f"- ABI: `{BUILD_ABI}`",
        f"- api_id: `{TG_API_ID[:2]}…` (hidden)",
    ]
    print("\n".join(lines))
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def main():
    print(f"Customizing Telegram source at {ROOT}")
    check_inputs()
    patch_gradle_properties()
    patch_account_limit()
    patch_build_vars()
    patch_app_name()
    patch_abis()
    patch_google_services()
    patch_account_type()
    install_icons()
    if errors:
        print(f"\n{len(errors)} problem(s) — the Telegram source no longer matches the anchors above.")
        sys.exit(1)
    write_summary()
    print("\nAll customizations applied.")


if __name__ == "__main__":
    main()
