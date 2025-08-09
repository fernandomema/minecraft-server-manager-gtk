"""
Controlador para manejar resource packs
"""
import os
import urllib.request
import urllib.parse
import threading
import hashlib
import json
from typing import Optional, Callable, List, Tuple, Dict
from gi.repository import GLib

from models.server import MinecraftServer


class ResourcePackController:
    def __init__(self):
        self.log_callback: Optional[Callable[[str], None]] = None
        self.packs_updated_callback: Optional[Callable[[List[Tuple[str, str]], Tuple[str, str]], None]] = None

    def set_log_callback(self, callback: Callable[[str], None]):
        """Establece el callback para mensajes de log"""
        self.log_callback = callback

    def set_packs_updated_callback(self, callback: Callable[[List[Tuple[str, str]], Tuple[str, str]], None]):
        """Establece el callback para cuando se actualizan los packs"""
        self.packs_updated_callback = callback

    def _log(self, message: str):
        if self.log_callback:
            self.log_callback(message)

    def _metadata_file(self, server_path: str) -> str:
        return os.path.join(server_path, ".resource_pack_metadata.json")

    def _load_metadata(self, server_path: str) -> Dict[str, Dict[str, str]]:
        try:
            with open(self._metadata_file(server_path), "r") as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_metadata(self, server_path: str, metadata: Dict[str, Dict[str, str]]):
        try:
            with open(self._metadata_file(server_path), "w") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            GLib.idle_add(self._log, f"Error saving resource pack metadata: {e}\n")

    def _get_resource_dir(self, server_path: str) -> str:
        resource_dir = os.path.join(server_path, "resourcepacks")
        os.makedirs(resource_dir, exist_ok=True)
        return resource_dir

    def _compute_sha1(self, file_path: str) -> str:
        sha1 = hashlib.sha1()
        with open(file_path, "rb") as f:
            while True:
                data = f.read(8192)
                if not data:
                    break
                sha1.update(data)
        return sha1.hexdigest()

    def get_resource_packs(self, server_path: str) -> List[Tuple[str, str]]:
        """Obtiene los resource packs disponibles"""
        resource_dir = self._get_resource_dir(server_path)
        metadata = self._load_metadata(server_path)
        packs = []
        for filename in os.listdir(resource_dir):
            if filename.endswith('.zip'):
                sha1 = metadata.get(filename, {}).get("sha1", "")
                packs.append((filename, sha1))
        return packs

    def get_active_pack(self, server_path: str) -> Tuple[str, str]:
        """Obtiene el pack activo desde server.properties"""
        props = self._read_properties(server_path)
        return props.get("resource-pack", ""), props.get("resource-pack-sha1", "")

    def refresh_resource_packs(self, server_path: str):
        packs = self.get_resource_packs(server_path)
        active = self.get_active_pack(server_path)
        if self.packs_updated_callback:
            self.packs_updated_callback(packs, active)

    def download_resource_pack(self, url: str, server: MinecraftServer,
                               callback: Optional[Callable[[bool, str], None]] = None):
        """Descarga un resource pack desde una URL"""
        def download():
            try:
                resource_dir = self._get_resource_dir(server.path)
                parsed = urllib.parse.urlparse(url)
                filename = os.path.basename(parsed.path) or "resource_pack.zip"
                target_path = os.path.join(resource_dir, filename)

                GLib.idle_add(self._log, f"Downloading resource pack from {url}...\n")
                urllib.request.urlretrieve(url, target_path)
                sha1 = self._compute_sha1(target_path)

                metadata = self._load_metadata(server.path)
                metadata[filename] = {"url": url, "sha1": sha1}
                self._save_metadata(server.path, metadata)

                GLib.idle_add(self._log, f"Downloaded resource pack '{filename}'.\n")
                GLib.idle_add(self.refresh_resource_packs, server.path)
                if callback:
                    GLib.idle_add(callback, True, filename)
            except Exception as e:
                GLib.idle_add(self._log, f"Error downloading resource pack: {e}\n")
                if callback:
                    GLib.idle_add(callback, False, str(e))

        threading.Thread(target=download, daemon=True).start()

    def activate_resource_pack(self, server: MinecraftServer, filename: str) -> bool:
        """Activa un resource pack"""
        metadata = self._load_metadata(server.path)
        pack_info = metadata.get(filename)
        if not pack_info:
            self._log(f"Metadata for resource pack '{filename}' not found.\n")
            return False

        url = pack_info.get("url", "")
        sha1 = pack_info.get("sha1", "")
        self._update_server_properties(server.path, {
            "resource-pack": url,
            "resource-pack-sha1": sha1
        })
        server.resource_pack = url
        server.resource_pack_sha1 = sha1
        self._log(f"Activated resource pack '{filename}'.\n")
        self.refresh_resource_packs(server.path)
        return True

    def deactivate_resource_pack(self, server: MinecraftServer):
        """Desactiva el resource pack"""
        self._update_server_properties(server.path, {
            "resource-pack": "",
            "resource-pack-sha1": ""
        })
        server.resource_pack = ""
        server.resource_pack_sha1 = ""
        self._log("Resource pack deactivated.\n")
        self.refresh_resource_packs(server.path)

    def _read_properties(self, server_path: str) -> Dict[str, str]:
        props_path = os.path.join(server_path, "server.properties")
        props: Dict[str, str] = {}
        if os.path.exists(props_path):
            with open(props_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        props[key] = value
        return props

    def _update_server_properties(self, server_path: str, updates: Dict[str, str]):
        props_path = os.path.join(server_path, "server.properties")
        lines = []
        if os.path.exists(props_path):
            with open(props_path, "r") as f:
                lines = f.readlines()
        positions: Dict[str, int] = {}
        for idx, line in enumerate(lines):
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=", 1)[0]
                positions[key] = idx
        for key, value in updates.items():
            if key in positions:
                lines[positions[key]] = f"{key}={value}\n"
            else:
                lines.append(f"{key}={value}\n")
        with open(props_path, "w") as f:
            f.writelines(lines)
