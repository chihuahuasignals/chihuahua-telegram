# Chihuahua Telegram

Your own build of Telegram for Android with the account limit raised (32 accounts instead of 3) plus:

- **Add to Group**, **Copy ID** and **Ban from all my groups** in every user's profile menu (⋮); **Copy ID** in group/channel menus too.
- The user's ID shown next to their online status in profiles (switchable).
- **Settings → Chihuahua**: ghost mode (no read receipts, no typing indicator, stay offline), video calls start with the back camera, hide the Stories bar, hide Telegram Premium promotions, toggle the ID display.

Nothing else in Telegram is changed. Built on GitHub's servers from the official
[DrKLO/Telegram](https://github.com/DrKLO/Telegram) source (GPL v2).

## Get the APK

1. Open the **Actions** tab. A yellow dot = building (1–3 hours), green tick = done, red cross = failed.
2. When it is green, open the **Releases** page on your phone and tap the `.apk` to install.
3. Android will ask to allow installs from your browser — allow it once.

Updates install over the old version and keep all your logins, because every build is signed with the same key.

## First-time setup (once)

Repository **Settings → Secrets and variables → Actions → New repository secret**, four times:

| Name | Value |
|---|---|
| `TG_API_ID` | your api_id from https://my.telegram.org |
| `TG_API_HASH` | your api_hash from https://my.telegram.org |
| `KEYSTORE_BASE64` | contents of `keystore-base64.txt` (the signing key, one long line) |
| `KEYSTORE_PASSWORD` | contents of `keystore-password.txt` |
| `ACTIVATION_CODE` | optional. A long passphrase; once set, every install asks for it once before it can be used. |

Keep `chihuahua-release.jks` and its password somewhere safe. Lose them and future builds
cannot update the installed app — you would have to uninstall and log in again.

## Keep it private

Make the repository **private** (Settings → General → Danger Zone → Change visibility) so only you can download
the APKs; builds then take ~45 minutes instead of ~22 and use your 2,000 free Actions minutes per month.
Add the `ACTIVATION_CODE` secret so that even a copied APK is useless without the code.

## Change something

Edit `config.env` on GitHub (pencil icon), commit, and a new build starts automatically.

- `APP_NAME` — the name under the icon.
- `MAX_ACCOUNTS` — the account cap (32).
- `TELEGRAM_COMMIT` — which Telegram version to build. To update to a newer Telegram, put the newest
  commit id from https://github.com/DrKLO/Telegram/commits/master here. If Telegram moved things
  around, the build fails with a clear "anchor found 0x" message in `customize.py` — that needs a small fix.
- `icons/` — the launcher icon PNGs (sticker of the real chihuahua). `icons/source/make_icons_v2.py sunset|ocean|candy` regenerates them; `sticker_v2.py` rebuilds the sticker from the background-removed photo.

You can also press **Actions → Build Android APK → Run workflow** to rebuild without changing anything.

## After installing

- Settings → Notifications and Sounds → scroll to the bottom → turn on **Keep-Alive Service** and
  **Background Connection**. This app cannot use Google push notifications (that needs a Firebase
  project registered to this package name), so it keeps its own connection open instead.
- Log-in codes for a third-party app are usually delivered to your existing Telegram session, not by SMS.
  Keep each account logged in on the official app the first time you add it here.
- Telegram's anti-spam runs on their servers. Many accounts on one phone doing marketing-like
  things get restricted no matter which app is used.

## Windows desktop

`.github/workflows/build-windows.yml` builds Telegram Desktop 7.1.5 (x64) with the same name, icon and
32-account limit, from `desktop/customize_desktop.py`. The third-party libraries take ~2-3 hours to
compile the first time and are then cached; a run that compiled them stops there — run it once more
(Actions → Build Windows desktop → Run workflow) and the second run produces the app in ~1-2 hours.
Releases are tagged `desktop-v…`; unzip and run the .exe (portable, data in `%APPDATA%\Chihuahua Telegram`).

## Files

- `.github/workflows/build-android.yml` — the build recipe GitHub runs.
- `customize.py` — the changes applied to Telegram's source (account limit, name, package, icon, API keys).
- `desktop/customize_desktop.py` — the same idea for Telegram Desktop; `icons/desktop/` its icons.
- `config.env` — the settings above.
- `icons/` — launcher icons.
