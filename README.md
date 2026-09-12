# Chihuahua Telegram

Your own build of Telegram for Android with the account limit raised (32 accounts instead of 3) plus:

- A row at the top of the Setup tab for a group of your choice — 🇸🇬 **@MassageInSG** here. Tapping it
  opens the group; joining is Telegram's own button at the bottom of the chat, so nobody is signed up
  to anything without pressing it. `config.env` sets the username and the label shown
  (`PROMO_GROUP`, `PROMO_TITLE` — the label is used as written, so it stays one tidy line whatever
  the group's real title is); clear `PROMO_GROUP` and the row is gone.
- **Add to Group**, **Copy ID** and **Ban from all my groups** in every user's profile menu (⋮).
- **Admins** in a group or channel's ⋮ menu — the full admin list in one tap, in any group you are in, not just ones you manage (Telegram only offers this through Manage Group, which needs admin rights).
- The estimated month the account was created shown next to their online status in profiles (worked out from the ID), and the user's ID on its own row below — tap it to copy. Both switchable.
- Group and channel profiles get the same ID row, under the invite link, in the form bots and the API use (`-100…` for supergroups and channels, `-…` for basic groups). Tap to copy.
- The Accounts card on the Settings tab shows each account's number under its name, with the flag of its country code (e.g. 🇸🇬 +65 8835 7983).
- Tap the phone number under your name at the top of the Settings tab to copy it (the number as shown, e.g. +44 7468 350735).
- The accounts there can be dragged into any order: hold the ≡ handle at the right of a row (or long-press the row) and move it. The order is kept and used wherever accounts are listed — the account switcher menu too. Telegram sorts accounts by the time they were added, so a new account still goes to the end.
- Tapping an account in that card switches to it and stays on the Settings tab (Telegram jumps to Chats).
- **Add Account** at the bottom of the Accounts card on the Settings tab, just above Account.
- **Sync Contacts** is unticked by default when adding an account (tick it yourself if you want it).
- The Contacts tab is a **Setup** tab instead: the settings worth touching on a freshly logged-in
  account, on one page, each changed where it stands — **Two-Step Verification**, **Terminate old
  sessions if inactive for**, **Delete my account if away for**, **Birthday**, and the privacy of
  **Last Seen & Online**, **Date of Birth** and **Invites** (Everybody / My Contacts / Nobody).
  Telegram spreads these over three screens and up to four taps each. Everything but Two-Step
  Verification applies the moment you pick it; exception lists you have set for a privacy rule are
  kept. The contact list is still there — a **Contacts** row at the bottom of the page, and on a
  long press of the tab.
- Every account that logs in is set once to **sessions 1 year**, **account 24 months** and
  **birthday visible to everybody**, against Telegram's 6 months, 18 months and contacts only. Once
  per account: change any of them by hand on its Setup tab afterwards and it stays changed. Accounts
  that were already logged in are left alone until **Settings → Chihuahua → New accounts → Apply to
  every account now** (which spaces the calls out), and the whole thing switches off there too.
- No **Invite Friends** list on the Contacts screen. Telegram lists everyone in the phone's own address book who is not on Telegram; this build shows only real Telegram contacts.
- The QR button on a profile's username row is grey instead of white (Telegram tints it for the title bar, so on this theme's light cards it was invisible).
- A **select-all** tick in the contact list's selection bar: long-press one contact, tap the tick and every contact of that account is selected (not just the ones on screen), then Delete. Telegram's own confirmation and undo still apply.
- The Administrators list shows one line of each admin's bio where Telegram shows "Promoted by …" (admins without a bio keep that text).
- The button row on a group profile is **Message · Mute · Admins · Recent Actions** (Telegram's Video Chat, Add Story and Leave are gone; Leave is still in the ⋮ menu). On a channel it is **Mute · Invite Links · Recent Actions** (no Live Stream or Add Story). Admin buttons only appear where you have the rights.
- Long-press a message in a group you moderate for three one-item actions, instead of Telegram's
  separate checkboxes. In every group you manage, each one first finds that sender's messages and
  reports them to Telegram for spam (the same call Telegram's own "Report spam" tick makes), then
  deletes every message *and* reaction of theirs there; they differ in what else they do:
  **Ban, wipe & report** (removes them from every group you manage, cannot rejoin) ·
  **Mute, wipe & report** (silences them — no posting, media, reactions, invites or pins — in every
  group you manage, without removing them) ·
  **Wipe & report** (clean-up only: no ban, no mute).
  Wipe runs the moment you tap it. Ban and Mute ask first, naming how many groups.
- In group chats the sender's estimated account age next to their name (red when newer than your threshold), so throwaway spam accounts stand out without opening profiles.
- A **Chihuahua 98** colour theme (Windows 98 palette: navy title bars, grey chrome, teal chat background), applied once on first start and listed under Settings → Chat Settings; the chat list is titled "Chihuahua".
- **Settings → Chihuahua**: the Ban-wipe-report item, flag new accounts in groups (with the age threshold), notifications on/off per logged-in account (only the first account you log in starts on; every account added after it starts off), ghost mode (no read receipts, no typing indicator, stay offline), video calls start with the back camera, hide the Stories bar, hide Telegram Premium promotions, toggle the ID display.

Nothing else in Telegram is changed. Built on GitHub's servers from the official
[DrKLO/Telegram](https://github.com/DrKLO/Telegram) source (GPL v2).

## Three apps

Every build produces **three** APKs from the same code: `Chihuahua1-….apk`, `Chihuahua2-….apk` and
`Chihuahua3-….apk`. The application id differs (`com.chihuahua.messenger`, `…2`, `…3`), so Android
treats them as separate apps and installs them side by side: 32 accounts each, their own
notifications, their own settings. Install any or all; they update independently from the same
release. Each has its own animal on the icon — two dogs and a cat.

`config.env` gives every app after the first a block of `APP<n>_` settings, and any of them
overrides the plain setting for that app alone; anything the block does not mention stays the same
as app one. That is the whole mechanism, so a new app is a block of five lines plus an icon folder.

**Chihuahua 3** uses it for two things the others do not do:

- After a login it offers to set up **Two-Step Verification** (once per account — answer either way
  and it does not come back, and it never asks for an account that already has a password).
- A newly logged-in account **joins the groups and channels in `APP3_AUTO_JOIN`, muted**. Joining is
  paced — one group every six seconds, one account at a time, marked done per account and group so
  nothing is tried twice and a restart carries on where it stopped. A Telegram rate limit parks that
  account until the app is started again rather than being retried into a harder limit.
  **Settings → Chihuahua → New accounts** shows how many are left and taps to resume. Clear
  `APP3_AUTO_JOIN` and it joins nothing.

  Worth knowing before you use it: many accounts on one phone joining the same list of groups is the
  shape Telegram's anti-spam is built to notice, whatever the accounts are for. The pacing helps; it
  is not a guarantee.

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
- `icons/` and `icons2/` — the launcher icons: each dog inside a chat bubble on the theme's navy-to-blue.
  `icons/source/make_icons_v3.py one|two` regenerates a set from that dog's background-removed photo
  (`cutout_u2net.png`, `cutout2_u2net.png`) — scale, framing and how far the ears may cross the rim are
  per-dog settings in its `PROFILES` table. `make_desktop_icons.py` builds the Windows set from dog one;
  the older sunset-sticker design is still there as `make_icons_v2.py`.

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
Releases are tagged `desktop-v…`; unzip and run the .exe. It is portable: on Windows, Telegram Desktop
keeps its data in a `tdata` folder **next to the .exe** whenever that folder is writable, and falls back
to `%APPDATA%\<app name>` only when it is not (Program Files, say). So to update, unzip the new .exe into
the same folder as the old one, beside `tdata`, and run it — logins carry over. The app's name is not
part of that path, so renaming the app changes nothing for an install that runs this way.

The desktop build has the name, icon, 32-account limit and the same three moderation items on a
message's right-click menu — **Ban, wipe & report**, **Mute, wipe & report**, **Wipe & report** —
with the same behaviour as on the phone: in every group you manage, find the sender's messages,
report them for spam, then delete every message and reaction of theirs; Wipe runs at once, Ban and
Mute ask first. The account rows in the ☰ menu and in Settings show each account's calling code
after the name (Quah Kee · +65). It also shows two extra rows in a
user's profile: **ID** (right-click → Copy ID) and **Account created** (the month estimated from
that ID). Both apps read the same anchor table out of `patches/ChihuahuaConfig.java`, so their
estimates cannot drift apart (`customize_desktop.py` generates `Telegram/SourceFiles/chihuahua_age.h`
from it). In group chats a sender under three months old gets ` · new` or ` · 2mo` after their name —
plain, not red, and shown only for new accounts, so the badge appearing at all is the warning.
**Admins** is in a group or channel's ⋮ menu here too. A big group's title bar shows **members, online** as the phone does — Telegram Desktop only counted online among the ~200 members it had loaded, so above that size it showed the member count alone, although the server sends the online figure; it is refreshed once a minute while the group is open. Scrolling through a busy group no longer stalls on the wheel: history is fetched 100 messages at a time, 6 screens ahead, instead of 50 and 3. In Settings, a left click on your phone number copies it (the right-click menu still has Copy Phone Number). The Android app is Java and the desktop app is
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
