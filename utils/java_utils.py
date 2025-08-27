import glob
import os
import shutil
import subprocess
from typing import List


def _run_host_command(command: List[str]) -> str:
    if os.environ.get("FLATPAK_ID"):
        flatpak_spawn = shutil.which("flatpak-spawn") or "/usr/libexec/flatpak-spawn"
        if os.path.exists(flatpak_spawn):
            command = [flatpak_spawn, "--host"] + command
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except Exception:
        return ""


def get_system_java_installations() -> List[str]:
    java_paths: List[str] = []

    for pattern in [
        "/usr/lib/jvm/*/bin/java",
        "/usr/lib/jvm/java-*/bin/java",
        "/usr/lib64/jvm/*/bin/java",
    ]:
        for path in glob.glob(pattern):
            if os.path.isfile(path) and os.access(path, os.X_OK):
                java_paths.append(path)

    if not java_paths:
        output = _run_host_command(["update-alternatives", "--list", "java"])
        if output:
            java_paths.extend(line.strip() for line in output.splitlines() if line.strip())

    if not java_paths:
        output = _run_host_command(["which", "java"])
        if output:
            java_paths.append(output.strip())

    return sorted(set(java_paths))


def open_java_download_page() -> bool:
    url = "https://adoptium.net"
    cmd = ["xdg-open", url]
    if os.environ.get("FLATPAK_ID"):
        cmd = ["flatpak-spawn", "--host"] + cmd
    try:
        subprocess.Popen(cmd)
        return True
    except Exception:
        return False
