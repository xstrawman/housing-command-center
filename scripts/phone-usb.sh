#!/usr/bin/env bash
# Phone over USB: port forward + install APK + open app
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"

if ! adb devices | grep -q 'device$'; then
  echo "No phone detected. Enable USB debugging on your Moto G."
  exit 1
fi

systemctl --user start hcc-web.service 2>/dev/null || true
adb reverse tcp:8787 tcp:8787
echo "Port forward: phone 127.0.0.1:8787 → PC:8787"

if [[ -f "$APK" ]]; then
  adb install -r "$APK"
  adb shell am start -n org.hcc.commandcenter/.MainActivity
  echo "Installed and launched Housing Command app."
else
  echo "APK not built yet. Run: $ROOT/android/scripts/build-apk.sh"
  echo "Phone can use Chrome → http://127.0.0.1:8787/today after adb reverse above."
fi