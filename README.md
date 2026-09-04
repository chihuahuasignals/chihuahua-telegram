# Chihuahua Telegram

Your own build of Telegram for Android with the account limit raised (32 accounts instead of 3) plus:

- **Add to Group**, **Copy ID** and **Ban from all my groups** in every user's profile menu (⋮); **Copy ID** in group/channel menus too.
- **Admins** in a group or channel's ⋮ menu — the full admin list in one tap, in any group you are in, not just ones you manage (Telegram only offers this through Manage Group, which needs admin rights).
- The estimated month the account was created shown next to their online status in profiles (worked out from the ID), and the user's ID on its own row below — tap it to copy. Both switchable.
- Long-press a message in a group you moderate for three one-item actions, instead of Telegram's
  separate checkboxes. All three delete every message *and* reaction of the sender and report them
  to Telegram for spam; they differ in what else they do:
  **Ban, wipe & report** (removes them from every group you manage, cannot rejoin) ·
  **Mute, wipe & report** (silences them — no posting, media, reactions, invites or pins — in every
  group you manage, without removing them) ·
  **Wipe & report** (clean-up only: no ban, no mute).
  All three cover every group you manage, and the confirmation names how many before you commit.
- In group chats the sender's estimated account age next to their name (red when newer than your threshold), so throwaway spam accounts stand out without opening profiles.
- A **Chihuahua 98** colour theme (Windows 98 palette: navy title bars, grey chrome, teal chat background), applied once on first start and listed under Settings → Chat Settings; the chat list is titled "Chihuahua".
- **Settings → Chihuahua**: the Ban-wipe-report item, flag new accounts in groups (with the age threshold), notifications on/off per logged-in account, ghost mode (no read receipts, no typing indicator, stay offline), video calls start with the back camera, hide the Stories bar, hide Telegram Premium promotions, toggle the ID display.

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

- **Notifications.** This app cannot use Google push (Telegram's push servers only deliver to tokens
  from Telegram's own Firebase project), so notifications come from Telegram's background connection.
  Settings → Chihuahua → Notifications → **Keep every account connected** turns on the keep-alive
  service and the background connection for every logged-in account on each start, which Telegram's
  own switches do not do (it stores Keep-Alive against the first account only, and Background
  Connection one account at a time). The same screen shows what the app is currently relying on.
  Telegram's keep-alive service is a plain background service that Android 8+ stops a minute after
  the app leaves the screen (harmless for the official app, which Firebase wakes); here it is a real
  foreground service with a quiet ongoing notification, declared `specialUse` so Android 15's
  six-hour daily cap on `dataSync` services does not apply.
- Android must also be told not to sleep the app. Settings → Chihuahua → Notifications offers
  **Stop Android sleeping the app** (the battery-optimisation exemption). On Samsung also check
  Settings → Battery → **Background usage limits** and remove the app from Sleeping/Deep sleeping
  apps; on Xiaomi/Redmi turn on **Autostart**. Locking the app in Recents helps on both.
- Log-in codes for a third-party app are usually delivered to your existing Telegram session, not by SMS.
  Keep each account logged in on the official app the first time you add it here.
- Telegram's anti-spam runs on their servers. Many accounts on one phone doing marketing-like
  things get restricted no matter which app is used.

## Windows desktop

`.github/workflows/build-windows.yml` builds Telegram Desktop 7.1.5 (x64, Release) with the same name, icon
and 32-account limit, from `desktop/customize_desktop.py`. The third-party libraries (Debug and Release —
a Release app cannot link against the Debug-only libraries Telegram's own CI builds) take ~2-3 hours to
compile the first time and are then cached; a run that compiled them stops there and automatically starts
a second run, which produces the app from the cached libraries in ~1-2 hours.
Releases are tagged `desktop-v…`; unzip and run the .exe (portable, data in `%APPDATA%\Chihuahua Telegram`).

The desktop build has the name, icon, 32-account limit and the same three moderation items on a
message's right-click menu — **Ban, wipe & report**, **Mute, wipe & report**, **Wipe & report** —
each covering every group you manage, exactly as on the phone. It also shows two extra rows in a
user's profile: **ID** (right-click → Copy ID) and **Account created** (the month estimated from
that ID). Both apps read the same anchor table out of `patches/ChihuahuaConfig.java`, so their
estimates cannot drift apart (`customize_desktop.py` generates `Telegram/SourceFiles/chihuahua_age.h`
from it). In group chats a sender under three months old gets ` · new` or ` · 2mo` after their name —
plain, not red, and shown only for new accounts, so the badge appearing at all is the warning.
**Admins** is in a group or channel's ⋮ menu here too. The Android app is Java and the desktop app is
C++/Qt, so nothing ports across: every feature is written twice. Still only on Android:
Settings → Chihuahua, so on desktop the age threshold is fixed at three months and every feature is
always on. Two Android features have no desktop equivalent and never will — the
back-camera default (no camera) and the notification keep-alive service (a desktop app holds its
own connection). `desktop/theme/ChihuahuaTelegram98.tdesktop-theme` is the Windows 98 palette for desktop —
in the app: Settings → Chat Settings → Choose theme → **Load from file**. Regenerate it with
`desktop/theme/make_desktop_theme.py <tdesktop>/Telegram/Resources/day-blue.tdesktop-theme`.
Keep the repository public while Windows builds are running: Windows minutes count double against the
2,000 free minutes of a private repository, and private repositories get slower runners.

## Files

- `.github/workflows/build-android.yml` — the build recipe GitHub runs.
- `customize.py` — the changes applied to Telegram's source (account limit, name, package, icon, API keys).
- `desktop/customize_desktop.py` — the same idea for Telegram Desktop; `icons/desktop/` its icons; `desktop/patch_prepare.py` drops the crash-report symbol tool (needs ATL) from the library recipe.
- `config.env` — the settings above.
- `icons/` — launcher icons.
