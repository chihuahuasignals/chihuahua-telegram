<#
    Setup-Chihuahua-PC.ps1
    ------------------------------------------------------------------
    Runs all the Chihuahua Telegram apps on this Windows PC inside
    Google's free Android emulator (the same idea as BlueStacks, but
    with no ads and no third-party account).

    What it does, start to finish:
      1. Finds the Android SDK (Android Studio's, if you have it) or
         downloads Google's command-line tools into
         %LOCALAPPDATA%\Android\Sdk.
      2. Installs the emulator, platform-tools (adb) and an x86_64
         Android 14 system image.
      3. Creates one virtual phone called "Chihuahua_PC".
      4. Starts it and waits for it to finish booting.
      5. Downloads every Chihuahua*.apk from the latest release and
         installs all of them side by side on that one virtual phone.

    Run it again any time to update the apps to the newest release.

    HOW TO RUN (first time, because the script is not signed):
      - Press Start, type "PowerShell", open Windows PowerShell.
      - Paste this and press Enter (adjust the path if you saved it
        somewhere else):
            powershell -ExecutionPolicy Bypass -File "$HOME\Downloads\Setup-Chihuahua-PC.ps1"

    REQUIREMENTS:
      - 64-bit Windows 10 or 11, ideally 16 GB RAM or more.
      - Hardware virtualization ON in the BIOS, and the Windows
        "Windows Hypervisor Platform" feature turned on (the script
        checks and tells you how if it is off).
      - About 10 GB of free disk space and a broadband connection for
        the one-time download.
#>

$ErrorActionPreference = 'Stop'
$ProgressPreference     = 'SilentlyContinue'   # faster Invoke-WebRequest

# ---- settings you could change -------------------------------------------
$Repo        = 'chihuahuasignals/chihuahua-telegram'
$ReleaseTag  = 'v12.10.1-build'        # the Android releases start with this
$AvdName     = 'Chihuahua_PC'
$ApiLevel    = 34                      # Android 14
$SysImage    = "system-images;android-$ApiLevel;google_apis;x86_64"
$Device      = 'pixel_6'
# --------------------------------------------------------------------------

function Say  ($m) { Write-Host "`n==> $m" -ForegroundColor Cyan }
function Note ($m) { Write-Host "    $m"   -ForegroundColor DarkGray }
function Warn ($m) { Write-Host "!!  $m"   -ForegroundColor Yellow }
function Die  ($m) { Write-Host "`nXX  $m" -ForegroundColor Red; Read-Host "`nPress Enter to close"; exit 1 }

try {

# ---- 0. sanity: 64-bit, virtualization ------------------------------------
Say "Checking this PC"
if (-not [Environment]::Is64BitOperatingSystem) { Die "This needs 64-bit Windows." }

$virt = (Get-CimInstance Win32_Processor).VirtualizationFirmwareEnabled
if ($virt -eq $false) {
    Warn "Hardware virtualization looks OFF in your BIOS."
    Warn "The emulator will be very slow or will not start until you turn on"
    Warn "Intel VT-x / AMD-V (SVM) in the BIOS. You can continue, but if the"
    Warn "virtual phone never boots, that is why."
} else {
    Note "Virtualization: on"
}

$hv = Get-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -ErrorAction SilentlyContinue
if ($hv -and $hv.State -ne 'Enabled') {
    Warn "The 'Windows Hypervisor Platform' feature is off. To turn it on, run this"
    Warn "once in an ADMIN PowerShell, then reboot:"
    Warn "    Enable-WindowsOptionalFeature -Online -FeatureName HypervisorPlatform -All"
}

# ---- 1. find or install the Android SDK -----------------------------------
Say "Locating the Android SDK"
$Sdk = $null
foreach ($c in @($env:ANDROID_HOME, $env:ANDROID_SDK_ROOT,
                 (Join-Path $env:LOCALAPPDATA 'Android\Sdk'))) {
    if ($c -and (Test-Path $c)) { $Sdk = $c; break }
}
if (-not $Sdk) { $Sdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk' }
Note "SDK folder: $Sdk"

function Find-SdkManager {
    Get-ChildItem -Path (Join-Path $Sdk 'cmdline-tools') -Recurse -Filter 'sdkmanager.bat' `
        -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
}
$SdkManager = Find-SdkManager

if (-not $SdkManager) {
    Say "Downloading Google's command-line tools (one time)"
    $tmp = Join-Path $env:TEMP 'cmdline-tools.zip'
    # Google keeps this URL stable; it is the Windows command-line tools bundle.
    $url = 'https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip'
    Invoke-WebRequest -Uri $url -OutFile $tmp
    $dest = Join-Path $Sdk 'cmdline-tools'
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    $staging = Join-Path $env:TEMP 'cmdline-tools-extract'
    if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
    Expand-Archive -Path $tmp -DestinationPath $staging -Force
    # The zip contains a "cmdline-tools" folder; Google wants it placed at .../cmdline-tools/latest
    $latest = Join-Path $dest 'latest'
    if (Test-Path $latest) { Remove-Item $latest -Recurse -Force }
    Move-Item (Join-Path $staging 'cmdline-tools') $latest
    Remove-Item $tmp, $staging -Recurse -Force -ErrorAction SilentlyContinue
    $SdkManager = Find-SdkManager
}
if (-not $SdkManager) { Die "Could not set up the Android command-line tools." }
Note "sdkmanager: $SdkManager"

$env:ANDROID_HOME     = $Sdk
$env:ANDROID_SDK_ROOT = $Sdk

# ---- 2. install the emulator, adb and the system image --------------------
Say "Installing the emulator, platform-tools and the Android $ApiLevel x86_64 image"
Note "(this is the big one-time download, a few GB)"

# Accept licenses: feed a stream of 'y'.
$yes = ("y`n" * 60)
$yes | & $SdkManager --sdk_root="$Sdk" --licenses | Out-Null
& $SdkManager --sdk_root="$Sdk" "platform-tools" "emulator" "$SysImage" "platforms;android-$ApiLevel"
if ($LASTEXITCODE -ne 0) { Die "sdkmanager failed while installing packages." }

$Adb         = Join-Path $Sdk 'platform-tools\adb.exe'
$Emulator    = Join-Path $Sdk 'emulator\emulator.exe'
$AvdManager  = Get-ChildItem -Path (Join-Path $Sdk 'cmdline-tools') -Recurse -Filter 'avdmanager.bat' `
                 -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName
foreach ($t in @($Adb, $Emulator, $AvdManager)) {
    if (-not (Test-Path $t)) { Die "Missing tool after install: $t" }
}

# ---- 3. create the virtual phone (once) -----------------------------------
Say "Setting up the '$AvdName' virtual phone"
$have = & $Emulator -list-avds 2>$null
if ($have -contains $AvdName) {
    Note "Already exists - keeping it (and whatever is logged in on it)."
} else {
    "no`n" | & $AvdManager create avd -n $AvdName -k "$SysImage" -d $Device --force
    if ($LASTEXITCODE -ne 0) { Die "Could not create the virtual phone." }
    # Give it enough RAM and internal storage for nine apps and their accounts.
    $cfg = Join-Path $env:USERPROFILE ".android\avd\$AvdName.avd\config.ini"
    if (Test-Path $cfg) {
        $lines = Get-Content $cfg | Where-Object { $_ -notmatch '^(hw\.ramSize|disk\.dataPartition\.size)=' }
        $lines += 'hw.ramSize=4096'
        $lines += 'disk.dataPartition.size=8G'
        Set-Content -Path $cfg -Value $lines -Encoding ASCII
    }
    Note "Created."
}

# ---- 4. start it and wait for boot ----------------------------------------
Say "Starting the virtual phone"
& $Adb start-server | Out-Null
$running = (& $Adb devices) -match 'emulator-\d+\s+device'
if (-not $running) {
    Start-Process -FilePath $Emulator `
        -ArgumentList @("-avd", $AvdName, "-netdelay", "none", "-netspeed", "full") `
        -WindowStyle Minimized
    Note "Waiting for it to appear (a phone window will open)..."
    & $Adb wait-for-device
}

Note "Waiting for Android to finish booting (first boot can take a few minutes)..."
$deadline = (Get-Date).AddMinutes(8)
do {
    Start-Sleep -Seconds 5
    $booted = (& $Adb shell getprop sys.boot_completed 2>$null).Trim()
    if ((Get-Date) -gt $deadline) { Die "The virtual phone did not finish booting. If virtualization is off in the BIOS, that is the usual cause." }
} until ($booted -eq '1')
Note "Booted."

# ---- 5. download the latest release APKs ----------------------------------
Say "Finding the latest Chihuahua release"
$headers = @{ 'User-Agent' = 'Chihuahua-PC-Setup'; 'Accept' = 'application/vnd.github+json' }
$releases = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repo/releases?per_page=30"
$rel = $releases |
    Where-Object { $_.tag_name -like "$ReleaseTag*" -and -not $_.draft } |
    Sort-Object { [datetime]$_.published_at } -Descending |
    Select-Object -First 1
if (-not $rel) { Die "No Android release found on GitHub yet." }
Note "Release: $($rel.tag_name)"

$apks = $rel.assets | Where-Object { $_.name -like 'Chihuahua*.apk' }
if (-not $apks) { Die "That release has no APKs yet - the build may still be running. Try again later." }

$dir = Join-Path $env:TEMP 'chihuahua-apks'
New-Item -ItemType Directory -Force -Path $dir | Out-Null
foreach ($a in $apks) {
    $out = Join-Path $dir $a.name
    Note "Downloading $($a.name)"
    Invoke-WebRequest -Headers $headers -Uri $a.browser_download_url -OutFile $out
}

# ---- 6. install all of them -----------------------------------------------
Say "Installing the apps on the virtual phone"
$ok = 0; $fail = @()
foreach ($a in ($apks | Sort-Object name)) {
    $out = Join-Path $dir $a.name
    Note "Installing $($a.name)"
    & $Adb install -r -g "$out" | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok++ } else { $fail += $a.name }
}

Say "Done"
Write-Host "    $ok app(s) installed on '$AvdName'." -ForegroundColor Green
if ($fail.Count) { Warn ("These did not install: " + ($fail -join ', ')) }
Write-Host ""
Write-Host "    The nine Chihuahua apps are in the virtual phone's app drawer." -ForegroundColor Green
Write-Host "    To open it again later WITHOUT re-running this script:" -ForegroundColor Green
Write-Host "        `"$Emulator`" -avd $AvdName" -ForegroundColor Green
Write-Host "    Re-run this script any time to update the apps to the newest release." -ForegroundColor Green

} catch {
    Die ("Something went wrong: " + $_.Exception.Message)
}

Read-Host "`nPress Enter to close"
