# Run the Chihuahua apps on a Windows PC

This runs all nine Chihuahua Telegram apps on your PC inside Google's free
Android emulator — the same idea as BlueStacks, but no ads and no third-party
account. One script does the whole thing.

Since the September/October 2026 builds, every APK is **universal** (`arm64-v8a`
+ `x86_64`), so the *same* file installs on your phone and on the PC emulator and
updates over the top of either. Nothing special to download — the script grabs
the latest release for you.

## What you need

- 64-bit Windows 10 or 11, ideally 16 GB RAM or more.
- Hardware virtualization **on** in the BIOS (Intel VT-x / AMD-V, sometimes
  called SVM), and the Windows **"Windows Hypervisor Platform"** feature turned
  on. The script checks both and tells you how to switch them on if they're off.
- About 10 GB of free disk space and a normal broadband connection for the
  one-time download.

## How to run it

1. Download **`Setup-Chihuahua-PC.ps1`** from this folder to, say, your Downloads.
2. Press **Start**, type **PowerShell**, open **Windows PowerShell**.
3. Paste this line and press Enter (change the path if you saved it elsewhere):

   ```powershell
   powershell -ExecutionPolicy Bypass -File "$HOME\Downloads\Setup-Chihuahua-PC.ps1"
   ```

The script will:

1. Find your Android SDK (Android Studio's, if you have it) or download Google's
   command-line tools into `%LOCALAPPDATA%\Android\Sdk`.
2. Install the emulator, `adb`, and an Android 14 x86_64 system image.
3. Create one virtual phone called **Chihuahua_PC** (4 GB RAM, 8 GB storage).
4. Start it and wait for it to boot (the first boot takes a few minutes).
5. Download every `Chihuahua*.apk` from the latest release and install all nine
   on that one virtual phone, side by side — just like on your S26.

When it finishes, the nine apps are in the virtual phone's app drawer. Log in to
each as you would on a phone.

## Afterwards

- **Open it again later** without re-running the setup:

  ```powershell
  "%LOCALAPPDATA%\Android\Sdk\emulator\emulator.exe" -avd Chihuahua_PC
  ```

- **Update the apps** to a newer release: just run the script again. It keeps the
  virtual phone and everything logged in on it, and reinstalls the apps over the
  top.

## Good to know

- Each account you log in on the emulator is a **new device session** on that
  account (manage them in Settings → Chihuahua → Devices, or Telegram's own
  Devices screen).
- To Telegram's anti-spam, many accounts run from one PC look the same as many
  accounts run from one phone. The emulator doesn't change that.
- If the virtual phone never finishes booting, virtualization is almost always
  off in the BIOS — that's the first thing to check.
