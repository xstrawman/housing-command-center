#!/usr/bin/env bash
# Prints copy-paste setup for Termux on Android (SSH + TUI)
cat <<'EOF'
=== Termux on your Moto G (F-Droid) ===

1. Install F-Droid (you have the APK in android-backup) → install Termux

2. In Termux:
   pkg update && pkg install openssh
   ssh YOUR_PC_USER@YOUR_PC_LAN_IP

3. On your PC (one time):
   sudo systemctl enable --now sshd
   # note your username: whoami
   # LAN IP: ip -4 addr show wlan0

4. Over SSH on phone:
   export HCC_URL=http://127.0.0.1:8787
   # if SSH session on PC, URL is localhost
   python3 ~/housing-command-center/scripts/hcc-tui

=== USB without Wi‑Fi ===
   On PC: adb reverse tcp:8787 tcp:8787
   In Termux (with adb port forward from PC side only for WebView app)
   Or SSH to PC while USB tethering / same network

=== Housing Command APK ===
   PC: ./android/scripts/build-apk.sh
   PC: ./scripts/phone-usb.sh
EOF