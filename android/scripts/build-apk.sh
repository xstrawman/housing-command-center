#!/usr/bin/env bash
# Build HCC Android APK (downloads local JDK + SDK if needed — no sudo)
set -euo pipefail

ANDROID_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TOOLS="$ANDROID_ROOT/.tools"
JDK_DIR="$TOOLS/jdk-17"
SDK_DIR="$TOOLS/android-sdk"
APK_OUT="$ANDROID_ROOT/app/build/outputs/apk/debug/app-debug.apk"

mkdir -p "$TOOLS"

if [[ ! -x "$JDK_DIR/bin/java" ]]; then
  echo "Downloading JDK 17…"
  JDK_ARCHIVE="$TOOLS/jdk.tar.gz"
  curl -fsSL -o "$JDK_ARCHIVE" \
    "https://api.adoptium.net/v3/binary/latest/17/ga/linux/x64/jdk/hotspot/normal/eclipse?project=jdk"
  rm -rf "$JDK_DIR"
  mkdir -p "$JDK_DIR"
  tar -xzf "$JDK_ARCHIVE" -C "$JDK_DIR" --strip-components=1
fi
export JAVA_HOME="$JDK_DIR"
export PATH="$JAVA_HOME/bin:$PATH"

if [[ ! -d "$SDK_DIR/cmdline-tools/latest" ]]; then
  echo "Downloading Android command-line tools…"
  CMDBUNDLE="$TOOLS/cmdline-tools.zip"
  curl -fsSL -o "$CMDBUNDLE" \
    "https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
  rm -rf "$SDK_DIR/cmdline-tools"
  mkdir -p "$SDK_DIR/cmdline-tools"
  unzip -q -o "$CMDBUNDLE" -d "$SDK_DIR/cmdline-tools"
  mv "$SDK_DIR/cmdline-tools/cmdline-tools" "$SDK_DIR/cmdline-tools/latest"
fi
export ANDROID_HOME="$SDK_DIR"
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

yes | sdkmanager --licenses >/dev/null 2>&1 || true
sdkmanager "platform-tools" "platforms;android-35" "build-tools;35.0.0"

cd "$ANDROID_ROOT"
if [[ ! -f ./gradlew ]]; then
  echo "Bootstrapping Gradle wrapper…"
  GRADLE_ZIP="$TOOLS/gradle-8.9-bin.zip"
  if [[ ! -f "$GRADLE_ZIP" ]]; then
    curl -fsSL -o "$GRADLE_ZIP" "https://services.gradle.org/distributions/gradle-8.9-bin.zip"
  fi
  unzip -q -o "$GRADLE_ZIP" -d "$TOOLS"
  "$TOOLS/gradle-8.9/bin/gradle" wrapper --gradle-version 8.9
fi

echo "Building debug APK…"
./gradlew assembleDebug --no-daemon

echo ""
echo "Built: $APK_OUT"
ls -lh "$APK_OUT"