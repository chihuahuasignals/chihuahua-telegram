#!/usr/bin/env bash
# Runs inside the GitHub Actions emulator step: install the APK, launch it, collect evidence.
set -x
OUT=smoke/result
mkdir -p "$OUT"
APK=$(ls out/*.apk | head -1)
PKG="${APP_PACKAGE:-com.chihuahua.messenger}"

adb wait-for-device
adb shell settings put global window_animation_scale 0 || true
adb install -r "$APK" 2>&1 | tee "$OUT/install.txt"
adb logcat -c || true

# Launch via the launcher intent, fall back to the activity name.
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 || adb shell am start -n "$PKG/org.telegram.ui.LaunchActivity"
sleep 45

adb logcat -d -v threadtime > "$OUT/logcat-full.txt" || true
PID=$(adb shell pidof "$PKG" | tr -d '\r\n ')
adb exec-out screencap -p > "$OUT/screen.png" || true
adb shell dumpsys activity activities 2>/dev/null | grep -E "mResumedActivity|topResumedActivity|ResumedActivity" | head -3 > "$OUT/resumed-activity.txt" || true

grep -E "FATAL EXCEPTION|Fatal signal|AndroidRuntime|DEBUG   :|backtrace:|#0[0-9] pc|$PKG" "$OUT/logcat-full.txt" | tail -n 600 > "$OUT/logcat-app.txt" || true
CRASH_LINES=$(grep -c -E "FATAL EXCEPTION|Fatal signal" "$OUT/logcat-full.txt" || true)

{
  echo "package=$PKG"
  echo "pid=$PID"
  echo "crash_lines=$CRASH_LINES"
  if [ -z "$PID" ] || [ "$CRASH_LINES" != "0" ]; then echo "result=crash"; else echo "result=alive"; fi
  echo "finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUT/STATUS"
cat "$OUT/STATUS"
tail -n 4000 "$OUT/logcat-full.txt" > "$OUT/logcat-tail.txt" || true
rm -f "$OUT/logcat-full.txt"
