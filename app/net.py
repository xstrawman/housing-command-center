from __future__ import annotations

import socket
import subprocess
import re


def lan_ip() -> str | None:
    try:
        out = subprocess.check_output(
            ["ip", "-4", "-o", "addr", "show", "scope", "global", "up"],
            text=True,
        )
        wifi: list[str] = []
        other: list[str] = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 4:
                continue
            iface, addr = parts[1], parts[3].split("/")[0]
            if re.match(r"^(lo|docker|br-|veth|virbr|tailscale)", iface):
                continue
            if iface.startswith(("wlan", "wlp", "wl")):
                wifi.append(addr)
            else:
                other.append(addr)
        return (wifi or other or [None])[0]
    except Exception:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None