# Run the Chihuahua apps on a Windows PC

All nine Chihuahua apps run on a PC inside Google's free Android emulator, the one that comes
with Android Studio — the same idea as BlueStacks, without the ads or a third-party account.
From build 85 on, every APK is **universal** (`arm64-v8a` + `x86_64`): the same file installs on
the phone and on the PC, runs natively on both, and updates over the top of either.

There is deliberately **no setup script**. The first version of this folder had one, and Windows
Defender blocks it ("This script contains malicious content") — to its script scanner, a script
that downloads tools and then runs them looks like malware. Everything below uses only what
Android Studio already installed. Don't switch Defender off for any of this.

## What you need

- Android Studio, set up once with its defaults (free, from developer.android.com/studio). Its
  setup wizard installs the emulator and `adb`, and creates a virtual phone called
  **`Medium_Phone`** (x86_64, Google Play). If you made your own phone instead, use its name from
  Android Studio's Device Manager, with spaces turned into underscores.
- Virtualization switched on (if `Medium_Phone` has ever started from Android Studio, it is).

## One time: a desktop icon that opens the phone

Opens the phone on its own, without Android Studio, like BlueStacks.

1. Right-click an empty spot on the desktop → **New** → **Shortcut**.
2. Paste this as the location → **Next**:

   ```
   %LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe -avd Medium_Phone
   ```

3. Name it **Chihuahua PC** → **Finish**.

Double-click it: a black log window opens, then the phone. Minimize the black window but don't
close it — closing it switches the phone off.

## Install or update the apps

1. Open the newest **Android** release on the Releases page — the one named
   *Chihuahua 12.10.1 (build N)*, not a `desktop-v…` one — and click the nine
   `Chihuahua1` … `Chihuahua9-…apk` files (skip the `SHA256SUMS` ones). If the browser warns,
   choose **Keep**.
2. With the phone on and showing its home screen, paste this into PowerShell:

   ```powershell
   Get-ChildItem "$HOME\Downloads\Chihuahua[1-9]-*.apk" | Group-Object { ($_.Name -split '-')[0] } | ForEach-Object { $_.Group | Sort-Object LastWriteTime | Select-Object -Last 1 } | ForEach-Object { "Installing $($_.Name)"; & "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe" -e install -r $_.FullName }
   ```

   Each app prints `Success`. If a Play Protect pop-up appears on the phone, tap
   **Install anyway**.

Run the same line after every new release. It installs only the **newest** download of each app
(old copies and `(1)` duplicates in Downloads are ignored), only onto the **emulator** (`-e`, so
never onto a phone plugged in by USB), and over the top (`-r`), so accounts stay logged in.

## Good to know

- Each account you log in on the PC is a **new device session** on that account (manage them in
  Settings → Chihuahua → Devices, or Telegram's own Devices screen).
- To Telegram's anti-spam, many accounts run from one PC look the same as many accounts run from
  one phone. The emulator doesn't change that.
- Feels slow switching between apps? Android Studio → Device Manager → **⋮** next to the phone →
  **Edit** → give it 4 GB of RAM.
