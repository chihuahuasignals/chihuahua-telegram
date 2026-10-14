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
  setup wizard installs the emulator and `adb`, and creates a virtual phone (x86_64, Google
  Play), named e.g. `Medium_Phone_API_35`. Any x86_64 phone you made in Device Manager works too.
- Virtualization switched on (if that phone has ever started from Android Studio, it is).

## One time: a desktop icon that opens the phone

Opens the phone on its own, without Android Studio, like BlueStacks.

1. Find the phone's exact name — paste this into PowerShell:

   ```powershell
   & "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -list-avds
   ```

   It prints one name per virtual phone, e.g. `Medium_Phone_API_35`. Use exactly that — not
   the name Device Manager shows, and not the folder under `.android\avd` (that one can be just
   `Medium_Phone.avd` while the phone is `Medium_Phone_API_35`).
2. Right-click an empty spot on the desktop → **New** → **Shortcut**.
3. Paste this as the location, with the name from step 1 at the end → **Next**:

   ```
   %LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe -avd Medium_Phone_API_35
   ```

4. Name it **Chihuahua PC** → **Finish**.
5. Right-click the new icon → **Properties** → **Run:** choose **Minimized** → **OK**.

Double-click it: the phone opens, and its black log window starts minimized in the taskbar. That
window is the phone's engine — it can't be switched off, only kept out of sight. Switch the phone
off with the **✕** on its side toolbar: it saves its state (the next start takes seconds) and the
black window closes with it. Closing the black window instead kills the phone without saving.

If the black window flashes and closes with no phone, the emulator quit on an error — usually a
wrong name after `-avd`. Run the shortcut's line in PowerShell to read the error (it prints
`Unknown AVD name` for a wrong name), then fix it under right-click → **Properties** → **Target**.

## Make it fast (once, before you log in to anything)

Android Studio's default phone gets 2 GB of RAM and 6 GB of storage — laggy with nine Telegram
apps, and too small for their photo caches. With the phone switched off, open its settings file
`%USERPROFILE%\.android\avd\<folder>.avd\config.ini` in Notepad (the folder can be plain
`Medium_Phone.avd`) and set these three lines:

```
hw.ramSize=8192
hw.gpu.mode=host
disk.dataPartition.size=17179869184
```

Write the RAM in plain megabytes: with Android Studio's own `hw.ramSize=2G` the emulator logged
`Increasing RAM size to 2048MB` and ran on 2 GB, while `8192` gives 8 GB. The CPU is already at the
emulator's maximum (6 cores) and `host` puts the graphics on the real graphics card. The bigger
storage needs one fresh start, which **erases the virtual phone** — hence before logging in:

```powershell
& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd Medium_Phone_API_35 -wipe-data
```

After that, use the desktop icon as usual. The emulator's start-up log shows what it is really
using (`hardware-qemu.ini` in the same folder holds the same values). Don't edit this phone in
Android Studio's Device Manager afterwards — it writes its own values back over these.

If the phone comes back with a dark screen that only lights up after you press its power button,
make it do a full start every time instead of resuming: in the same `config.ini` set

```
fastboot.forceColdBoot=yes
fastboot.forceFastBoot=no
```

Each start then takes about 30–40 seconds instead of a few, but the screen always comes up on its
own. Apps and logins are kept — they live on the phone's storage, not in the saved state.

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

## A second phone

Two virtual phones spread the apps out, so one problem can't take everything down. A phone is a
pointer file plus a folder in `%USERPROFILE%\.android\avd\`: `<name>.ini` (with `path=` and
`path.rel=` to the folder) and `<name>.avd\config.ini`. Copy the first phone's `config.ini`,
change `AvdId` and `avd.ini.displayname`, and the emulator builds the phone's storage on its first
start (1–2 minutes). Android Studio's Device Manager → **+** does the same with clicks. Give it its
own desktop shortcut (`emulator.exe -avd <name>`), and set its `emulator-user.ini` `window.x` so it
opens beside the first phone.

Both phones can run at once; each uses its own RAM, so keep the total well inside the PC's memory.
To install apps on one of them, **have only that phone open**: with two running, `adb -e` can't
tell which one you mean. Back up both by copying the whole `avd` folder.

## Good to know

- Each account you log in on the PC is a **new device session** on that account (manage them in
  Settings → Chihuahua → Devices, or Telegram's own Devices screen).
- To Telegram's anti-spam, many accounts run from one PC look the same as many accounts run from
  one phone. The emulator doesn't change that.
