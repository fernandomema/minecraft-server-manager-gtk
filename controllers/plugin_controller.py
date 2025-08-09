"""
Controlador para manejar plugins y mods
"""
import json
import urllib.request
import urllib.parse
import threading
import os
import socket
import zipfile
import re
from typing import List, Dict, Optional, Callable
from gi.repository import GLib

from models.plugin import Plugin
from utils.constants import (
    MODRINTH_API_BASE_URL,
    SPIGET_API_BASE_URL,
    CURSEFORGE_API_BASE_URL,
)
from utils.file_utils import get_plugins_and_mods, load_json_file, save_json_file


class PluginController:
    def __init__(self):
        self.search_callback: Optional[Callable[[str], None]] = None
        self.plugins_updated_callback: Optional[Callable[[List[Plugin]], None]] = None
    
    def set_search_callback(self, callback: Callable[[str], None]):
        """Establece el callback para mensajes de búsqueda"""
        self.search_callback = callback
    
    def set_plugins_updated_callback(self, callback: Callable[[List[Plugin]], None]):
        """Establece el callback para cuando se actualizan los plugins"""
        self.plugins_updated_callback = callback
    
    def _log(self, message: str):
        """Envía un mensaje de log"""
        if self.search_callback:
            self.search_callback(message)

    def _detect_plugin_type(self, filename: str) -> Optional[str]:
        """Detecta si un archivo es un plugin o mod.

        Reutiliza la heurística simple utilizada en la vista. Devuelve
        "plugin" o "mod". Si el archivo no es un JAR o no puede
        determinarse, devuelve ``None``.
        """
        lower = filename.lower()
        if not lower.endswith(".jar"):
            return None

        if "/mods/" in lower or any(keyword in lower for keyword in ["forge", "fabric", "quilt", "mod"]):
            return "mod"
        return "plugin"
    
    def _get_plugin_metadata_file(self, server_path: str) -> str:
        """Obtiene la ruta del archivo de metadatos de plugins"""
        return os.path.join(server_path, ".plugin_metadata.json")
    
    def _load_plugin_metadata(self, server_path: str) -> Dict[str, Dict]:
        """Carga los metadatos de plugins de un servidor"""
        metadata_file = self._get_plugin_metadata_file(server_path)
        if not os.path.exists(metadata_file):
            return {}
        try:
            data = load_json_file(metadata_file)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            GLib.idle_add(self._log, f"Error loading plugin metadata: {e}\n")
            return {}
    
    def _save_plugin_metadata(self, server_path: str, metadata: Dict[str, Dict]) -> bool:
        """Guarda los metadatos de plugins de un servidor"""
        metadata_file = self._get_plugin_metadata_file(server_path)
        try:
            save_json_file(metadata_file, metadata)
            return True
        except Exception as e:
            GLib.idle_add(self._log, f"Error saving plugin metadata: {e}\n")
            return False
    
    def _add_plugin_metadata(
        self,
        server_path: str,
        plugin_name: str,
        install_method: str,
        project_id: Optional[str] = None,
        plugin_type: str = "plugin",
    ):
        """Añade metadatos para un plugin"""
        metadata = self._load_plugin_metadata(server_path)
        metadata[plugin_name] = {
            "install_method": install_method.capitalize(),
            "project_id": project_id,
            "installed_at": __import__("datetime").datetime.now().isoformat(),
            "type": plugin_type,
        }
        self._save_plugin_metadata(server_path, metadata)
    
    def _remove_plugin_metadata(self, server_path: str, plugin_name: str):
        """Elimina metadatos de un plugin"""
        metadata = self._load_plugin_metadata(server_path)
        if plugin_name in metadata:
            del metadata[plugin_name]
            self._save_plugin_metadata(server_path, metadata)

    def _extract_version_from_jar(self, file_path: str) -> str:
        """Obtiene la versión desde los metadatos del JAR.

        Soporta formatos de plugins de Bukkit/Spigot (plugin.yml), mods de
        Fabric/Quilt (fabric.mod.json/quilt.mod.json) y mods de Forge
        (mods.toml). Si no se puede determinar la versión se devuelve
        "Unknown".
        """
        try:
            with zipfile.ZipFile(file_path, "r") as jar:
                if "plugin.yml" in jar.namelist():
                    data = jar.read("plugin.yml").decode("utf-8", errors="ignore")
                    match = re.search(r"^version:\s*(.+)$", data, re.MULTILINE)
                    if match:
                        return match.group(1).strip()

                for json_file in ["fabric.mod.json", "quilt.mod.json"]:
                    if json_file in jar.namelist():
                        try:
                            meta = json.loads(jar.read(json_file).decode("utf-8"))
                            version = meta.get("version")
                            if version:
                                return str(version)
                        except Exception:
                            pass

                for toml_file in ["mods.toml", "META-INF/mods.toml"]:
                    if toml_file in jar.namelist():
                        text = jar.read(toml_file).decode("utf-8", errors="ignore")
                        match = re.search(r'version\s*=\s*"([^"]+)"', text)
                        if match:
                            return match.group(1).strip()
        except Exception as e:
            GLib.idle_add(self._log, f"Error extracting version from {os.path.basename(file_path)}: {e}\n")

        return "Unknown"
    
    def get_local_plugins(self, server_path: str) -> List[Plugin]:
        """Obtiene la lista de plugins locales de un servidor"""
        plugins = []
        items = get_plugins_and_mods(server_path)
        metadata = self._load_plugin_metadata(server_path)
        
        for filename, full_path in items:
            plugin_name = filename.replace('.jar', '')
            plugin_metadata = metadata.get(plugin_name, {})

            install_method = plugin_metadata.get("install_method", "Manual")
            project_id = plugin_metadata.get("project_id")
            version = self._extract_version_from_jar(full_path)

            plugin = Plugin(
                name=plugin_name,
                source="Local",
                version=version,
                file_path=full_path,
                install_method=install_method
            )
            plugin.project_id = project_id
            plugins.append(plugin)
        
        return plugins
    
    def refresh_local_plugins(self, server_path: str):
        """Refresca la lista de plugins locales y notifica a la vista"""
        plugins = self.get_local_plugins(server_path)
        if self.plugins_updated_callback:
            self.plugins_updated_callback(plugins)
    
    def search_modrinth_plugins(self, query: str, callback: Callable[[List[Plugin]], None], search_type: str = ""):
        """Busca plugins en Modrinth de forma asíncrona
        
        Args:
            query: Término de búsqueda
            callback: Función callback para los resultados
            search_type: Tipo de búsqueda ("plugin", "mod", o "" para ambos)
        """
        def perform_search():
            try:
                encoded_query = urllib.parse.quote(query)
                url = f"{MODRINTH_API_BASE_URL}/search?query={encoded_query}"
                
                # Agregar facets para filtrar por tipo de proyecto si se especifica
                if search_type in ["plugin", "mod"]:
                    facet = urllib.parse.quote(f'[["project_type:{search_type}"]]')
                    url += f"&facets={facet}"
                
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 'MinecraftServerManager/1.0')
                
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode())
                
                plugins = []
                if data and "hits" in data:
                    total_hits = len(data['hits'])
                    filtered_count = 0
                    
                    for hit in data["hits"]:
                        # Usar el atributo 'project_type' directamente de la respuesta
                        project_type = hit.get("project_type", "").lower()
                        title = hit.get('title', 'Unknown')
                        categories = hit.get("categories", [])
                        
                        # Solo incluir mods y plugins, excluir modpacks y otros tipos
                        if project_type not in ["mod", "plugin"]:
                            continue
                        
                        # Detectar plugins basándose en las categorías
                        plugin_categories = ["spigot", "paper", "bukkit", "purpur", "waterfall", "velocity"]
                        is_plugin = any(cat.lower() in plugin_categories for cat in categories)
                        
                        # Si tiene categorías de servidor, es un plugin, no un mod
                        if is_plugin:
                            project_type = "plugin"
                            
                        filtered_count += 1
                            
                        name = hit.get("title", "N/A")
                        description = hit.get("description", "")[:200] + "..." if len(hit.get("description", "")) > 200 else hit.get("description", "")
                        icon_url = hit.get("icon_url", "")
                        project_id = hit.get("project_id", "") or hit.get("id", "")  # Obtener el ID del proyecto
                        version = "Latest"
                        if hit.get("versions"):
                            version = hit["versions"][0] if hit["versions"] else "Latest"
                        
                        plugin = Plugin(
                            name=name,
                            source="Modrinth",
                            version=version,
                            description=description
                        )
                        # Usar el tipo de proyecto directamente de la API de Modrinth
                        plugin.project_type = project_type
                        # Añadir la URL del icono como atributo
                        plugin.icon_url = icon_url
                        # Añadir el ID del proyecto
                        plugin.project_id = project_id
                        plugins.append(plugin)
                    
                    search_type_desc = search_type or 'both plugins and mods'
                    GLib.idle_add(self._log, f"Found {len(plugins)} {search_type_desc} from Modrinth.\n")
                else:
                    GLib.idle_add(self._log, "No results found from Modrinth.\n")
                
                GLib.idle_add(callback, plugins)
                
            except urllib.error.HTTPError as e:
                GLib.idle_add(self._log, f"DEBUG: HTTP Error {e.code}: {e.reason}\n")
                GLib.idle_add(callback, [])
            except socket.timeout:
                GLib.idle_add(self._log, "DEBUG: Connection to Modrinth timed out\n")
                GLib.idle_add(callback, [])
            except urllib.error.URLError as e:
                if isinstance(e.reason, socket.timeout):
                    GLib.idle_add(self._log, "DEBUG: Connection to Modrinth timed out\n")
                else:
                    GLib.idle_add(self._log, f"DEBUG: URL Error: {e.reason}\n")
                GLib.idle_add(callback, [])
            except Exception as e:
                GLib.idle_add(self._log, f"DEBUG: Error searching Modrinth: {e}\n")
                GLib.idle_add(callback, [])
        
        threading.Thread(target=perform_search, daemon=True).start()

    def search_spigot_plugins(self, query: str, callback: Callable[[List[Plugin]], None]):
        """Busca plugins en Spigot (usando Spiget API) de forma asíncrona"""

        def perform_search():
            try:
                encoded_query = urllib.parse.quote(query)
                url = f"{SPIGET_API_BASE_URL}/search/resources/{encoded_query}?size=20"
                request = urllib.request.Request(url)
                request.add_header("User-Agent", "MinecraftServerManager/1.0")
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode())

                plugins = []
                for item in data:
                    name = item.get("name", "N/A")
                    resource_id = str(item.get("id", ""))
                    description = item.get("tag", "")
                    plugin = Plugin(
                        name=name,
                        source="Spigot",
                        version="Latest",
                        description=description,
                        install_method="Spigot",
                    )
                    plugin.project_id = resource_id
                    plugin.project_type = "plugin"
                    plugin.icon_url = f"{SPIGET_API_BASE_URL}/resources/{resource_id}/icon"
                    plugins.append(plugin)

                GLib.idle_add(self._log, f"Found {len(plugins)} plugins from Spigot.\n")
                GLib.idle_add(callback, plugins)

            except Exception as e:
                GLib.idle_add(self._log, f"DEBUG: Error searching Spigot: {e}\n")
                GLib.idle_add(callback, [])

        threading.Thread(target=perform_search, daemon=True).start()

    def search_curseforge_plugins(self, query: str, callback: Callable[[List[Plugin]], None], search_type: str = ""):
        """Busca plugins o mods en CurseForge de forma asíncrona"""

        def perform_search():
            api_key = os.environ.get("CURSEFORGE_API_KEY")
            if not api_key:
                GLib.idle_add(self._log, "DEBUG: Missing CurseForge API key\n")
                GLib.idle_add(callback, [])
                return

            try:
                encoded_query = urllib.parse.quote(query)
                url = f"{CURSEFORGE_API_BASE_URL}/mods/search?gameId=432&searchFilter={encoded_query}"

                # Filtrar por tipo si se especifica (mods vs plugins)
                if search_type == "mod":
                    url += "&classId=6"
                elif search_type == "plugin":
                    url += "&classId=5"

                request = urllib.request.Request(url)
                request.add_header("x-api-key", api_key)
                request.add_header("User-Agent", "MinecraftServerManager/1.0")

                with urllib.request.urlopen(request, timeout=10) as response:
                    data = json.loads(response.read().decode())

                plugins = []
                for item in data.get("data", []):
                    name = item.get("name", "N/A")
                    description = item.get("summary", "")
                    project_id = str(item.get("id", ""))
                    logo = item.get("logo") or {}
                    icon_url = logo.get("url", "")
                    class_id = item.get("classId", 6)
                    project_type = "plugin" if class_id == 5 else "mod"
                    plugin = Plugin(
                        name=name,
                        source="CurseForge",
                        version="Latest",
                        description=description,
                        install_method="CurseForge",
                    )
                    plugin.project_id = project_id
                    plugin.icon_url = icon_url
                    plugin.project_type = project_type
                    plugins.append(plugin)

                GLib.idle_add(self._log, f"Found {len(plugins)} results from CurseForge.\n")
                GLib.idle_add(callback, plugins)

            except Exception as e:
                GLib.idle_add(self._log, f"DEBUG: Error searching CurseForge: {e}\n")
                GLib.idle_add(callback, [])

        threading.Thread(target=perform_search, daemon=True).start()

    def download_modrinth_plugin(self, plugin_name: str, project_id: str, server_path: str, callback: Callable[[bool, str], None]):
        """Descarga un plugin desde Modrinth de forma asíncrona
        
        Args:
            plugin_name: Nombre del plugin
            project_id: ID del proyecto en Modrinth (extraído de la URL del icono o búsqueda)
            server_path: Ruta del servidor donde instalar
            callback: Función callback con (success: bool, message: str)
        """
        def perform_download():
            try:
                GLib.idle_add(self._log, f"Starting download of {plugin_name} from Modrinth...\n")
                
                # Obtener información del proyecto
                project_url = f"{MODRINTH_API_BASE_URL}/project/{project_id}"
                request = urllib.request.Request(project_url)
                request.add_header('User-Agent', 'MinecraftServerManager/1.0')
                
                with urllib.request.urlopen(request, timeout=10) as response:
                    project_data = json.loads(response.read().decode())
                
                # Obtener las versiones del proyecto
                versions_url = f"{MODRINTH_API_BASE_URL}/project/{project_id}/version"
                request = urllib.request.Request(versions_url)
                request.add_header('User-Agent', 'MinecraftServerManager/1.0')
                
                with urllib.request.urlopen(request, timeout=10) as response:
                    versions_data = json.loads(response.read().decode())
                
                if not versions_data:
                    GLib.idle_add(callback, False, "No versions available for this plugin")
                    return
                
                # Obtener la última versión compatible
                latest_version = None
                for version in versions_data:
                    # Buscar versión compatible con el servidor (puedes filtrar por game_versions si es necesario)
                    if version.get("files"):
                        latest_version = version
                        break
                
                if not latest_version:
                    GLib.idle_add(callback, False, "No compatible version found")
                    return
                
                # Obtener el archivo de descarga
                download_file = latest_version["files"][0]  # Tomar el primer archivo
                download_url = download_file["url"]
                filename = download_file["filename"]
                
                # Crear directorio de plugins/mods según el tipo
                project_type = project_data.get("project_type", "mod").lower()
                categories = project_data.get("categories", [])
                
                # Verificar si hay información de loaders
                loaders = project_data.get("loaders", [])
                
                # Detectar plugins basándose en las categorías O loaders
                plugin_categories = ["spigot", "paper", "bukkit", "purpur", "waterfall", "velocity"]
                plugin_loaders = ["bukkit", "spigot", "paper", "purpur", "waterfall", "velocity"]
                
                is_plugin_by_categories = any(cat.lower() in plugin_categories for cat in categories)
                is_plugin_by_loaders = any(loader.lower() in plugin_loaders for loader in loaders)
                is_plugin = is_plugin_by_categories or is_plugin_by_loaders
                
                # Si tiene categorías de servidor, es un plugin, no un mod
                if is_plugin:
                    project_type = "plugin"
                
                if project_type == "plugin":
                    plugins_dir = os.path.join(server_path, "plugins")
                else:
                    plugins_dir = os.path.join(server_path, "mods")
                
                os.makedirs(plugins_dir, exist_ok=True)
                
                # Descargar el archivo
                file_path = os.path.join(plugins_dir, filename)
                download_request = urllib.request.Request(download_url)
                download_request.add_header('User-Agent', 'MinecraftServerManager/1.0')
                with urllib.request.urlopen(download_request, timeout=10) as response, open(file_path, "wb") as out_file:
                    out_file.write(response.read())
                
                # Solo guardar metadatos, no agregar a la lista (se hará en refresh)
                plugin_name_clean = os.path.splitext(filename)[0]
                self._add_plugin_metadata(
                    server_path,
                    plugin_name_clean,
                    "Modrinth",
                    project_id,
                    project_type
                )
                
                GLib.idle_add(callback, True, f"Successfully downloaded {plugin_name}")
                GLib.idle_add(self._log, f"Download completed: {filename}\n")
                
            except urllib.error.HTTPError as e:
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
            except socket.timeout:
                error_msg = "Connection to Modrinth timed out"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
            except urllib.error.URLError as e:
                if isinstance(e.reason, socket.timeout):
                    error_msg = "Connection to Modrinth timed out"
                else:
                    error_msg = f"URL Error: {e.reason}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
            except Exception as e:
                error_msg = f"Download error: {str(e)}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
        
        threading.Thread(target=perform_download, daemon=True).start()

    def download_spigot_plugin(self, plugin_name: str, resource_id: str, server_path: str, callback: Callable[[bool, str], None]):
        """Descarga un plugin desde Spigot de forma asíncrona"""

        def perform_download():
            try:
                GLib.idle_add(self._log, f"Starting download of {plugin_name} from Spigot...\n")
                download_url = f"{SPIGET_API_BASE_URL}/resources/{resource_id}/download"
                request = urllib.request.Request(download_url)
                request.add_header("User-Agent", "MinecraftServerManager/1.0")
                plugins_dir = os.path.join(server_path, "plugins")
                os.makedirs(plugins_dir, exist_ok=True)
                file_path = os.path.join(plugins_dir, f"{plugin_name}.jar")
                with urllib.request.urlopen(request, timeout=20) as response, open(file_path, "wb") as out_file:
                    out_file.write(response.read())

                plugin_name_clean = os.path.splitext(os.path.basename(file_path))[0]
                self._add_plugin_metadata(server_path, plugin_name_clean, "Spigot", resource_id, "plugin")

                GLib.idle_add(callback, True, f"Successfully downloaded {plugin_name}")
                GLib.idle_add(self._log, f"Download completed: {os.path.basename(file_path)}\n")

            except urllib.error.HTTPError as e:
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
            except Exception as e:
                error_msg = f"Download error: {str(e)}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")

        threading.Thread(target=perform_download, daemon=True).start()

    def download_curseforge_plugin(self, plugin_name: str, project_id: str, server_path: str, callback: Callable[[bool, str], None]):
        """Descarga un mod o plugin desde CurseForge de forma asíncrona"""

        def perform_download():
            api_key = os.environ.get("CURSEFORGE_API_KEY")
            if not api_key:
                GLib.idle_add(callback, False, "Missing CurseForge API key")
                return

            try:
                GLib.idle_add(self._log, f"Starting download of {plugin_name} from CurseForge...\n")
                files_url = f"{CURSEFORGE_API_BASE_URL}/mods/{project_id}/files"
                request = urllib.request.Request(files_url)
                request.add_header("x-api-key", api_key)
                request.add_header("User-Agent", "MinecraftServerManager/1.0")
                with urllib.request.urlopen(request, timeout=10) as response:
                    files_data = json.loads(response.read().decode())

                if not files_data.get("data"):
                    GLib.idle_add(callback, False, "No files available for this project")
                    return

                latest_file = files_data["data"][0]
                download_url = latest_file.get("downloadUrl")
                filename = latest_file.get("fileName", f"{plugin_name}.jar")

                request = urllib.request.Request(download_url)
                request.add_header("User-Agent", "MinecraftServerManager/1.0")

                # Determinar directorio según tipo
                project_type = "plugin" if latest_file.get("classId") == 5 else "mod"
                if project_type == "plugin":
                    target_dir = os.path.join(server_path, "plugins")
                else:
                    target_dir = os.path.join(server_path, "mods")
                os.makedirs(target_dir, exist_ok=True)

                file_path = os.path.join(target_dir, filename)
                with urllib.request.urlopen(request, timeout=20) as response, open(file_path, "wb") as out_file:
                    out_file.write(response.read())

                plugin_name_clean = os.path.splitext(filename)[0]
                self._add_plugin_metadata(server_path, plugin_name_clean, "CurseForge", project_id, project_type)

                GLib.idle_add(callback, True, f"Successfully downloaded {plugin_name}")
                GLib.idle_add(self._log, f"Download completed: {filename}\n")

            except urllib.error.HTTPError as e:
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")
            except Exception as e:
                error_msg = f"Download error: {str(e)}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Download failed: {error_msg}\n")

        threading.Thread(target=perform_download, daemon=True).start()

    def update_plugin(self, plugin: Plugin, server_path: str, callback: Callable[[bool, str], None]):
        """Actualiza un plugin instalado desde Modrinth

        Args:
            plugin: Plugin a actualizar. Debe tener project_id válido
            server_path: Ruta del servidor donde está instalado el plugin
            callback: Función callback con (success: bool, message: str)
        """

        if getattr(plugin, "install_method", "Modrinth") != "Modrinth":
            GLib.idle_add(callback, False, f"Update from {plugin.install_method} is not supported")
            return

        def perform_update():
            if not plugin.project_id:
                GLib.idle_add(callback, False, "No project ID available for this plugin")
                return

            try:
                GLib.idle_add(self._log, f"Checking Modrinth for updates of {plugin.name}...\n")

                # Obtener versiones del proyecto
                versions_url = f"{MODRINTH_API_BASE_URL}/project/{plugin.project_id}/version"
                request = urllib.request.Request(versions_url)
                request.add_header('User-Agent', 'MinecraftServerManager/1.0')

                with urllib.request.urlopen(request) as response:
                    versions_data = json.loads(response.read().decode())

                if not versions_data:
                    GLib.idle_add(callback, False, "No versions available for this plugin")
                    return

                # Tomar la primera versión que tenga archivos
                latest_version = None
                for version in versions_data:
                    if version.get("files"):
                        latest_version = version
                        break

                if not latest_version:
                    GLib.idle_add(callback, False, "No compatible version found")
                    return

                download_file = latest_version["files"][0]
                download_url = download_file["url"]
                filename = download_file["filename"]

                # Verificar si ya está actualizado comparando el nombre del archivo
                if plugin.file_path and os.path.basename(plugin.file_path) == filename:
                    GLib.idle_add(callback, True, "Plugin is already up to date")
                    return

                plugin_dir = os.path.dirname(plugin.file_path) if plugin.file_path else os.path.join(server_path, "plugins")
                os.makedirs(plugin_dir, exist_ok=True)
                new_file_path = os.path.join(plugin_dir, filename)

                GLib.idle_add(self._log, f"Downloading {filename}...\n")
                urllib.request.urlretrieve(download_url, new_file_path)

                # Eliminar el archivo antiguo
                if plugin.file_path and os.path.exists(plugin.file_path):
                    os.remove(plugin.file_path)

                # Actualizar metadatos
                self._remove_plugin_metadata(server_path, plugin.name)
                new_plugin_name = os.path.splitext(filename)[0]
                self._add_plugin_metadata(server_path, new_plugin_name, plugin.install_method, plugin.project_id)

                GLib.idle_add(callback, True, f"Updated {plugin.name}")
                GLib.idle_add(self._log, f"Update completed: {filename}\n")

            except urllib.error.HTTPError as e:
                error_msg = f"HTTP Error {e.code}: {e.reason}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Update failed: {error_msg}\n")
            except Exception as e:
                error_msg = f"Update error: {str(e)}"
                GLib.idle_add(callback, False, error_msg)
                GLib.idle_add(self._log, f"Update failed: {error_msg}\n")

        threading.Thread(target=perform_update, daemon=True).start()

    def remove_local_plugin(self, plugin: Plugin, server_path: str = None) -> bool:
        """Elimina un plugin local"""
        if not plugin.is_local() or not plugin.file_path:
            self._log("Cannot remove non-local plugin or plugin without file path.\n")
            return False
        
        try:
            if os.path.exists(plugin.file_path):
                os.remove(plugin.file_path)
                
                # Eliminar metadatos si tenemos la ruta del servidor
                if server_path:
                    self._remove_plugin_metadata(server_path, plugin.name)
                else:
                    # Intentar extraer la ruta del servidor desde la ruta del archivo
                    server_path_guess = os.path.dirname(os.path.dirname(plugin.file_path))
                    if os.path.exists(server_path_guess):
                        self._remove_plugin_metadata(server_path_guess, plugin.name)
                
                self._log(f"Removed plugin: {plugin.name}\n")
                return True
            else:
                self._log(f"Plugin file not found: {plugin.file_path}\n")
                return False
        except Exception as e:
            self._log(f"Error removing plugin: {e}\n")
            return False
    
    def add_local_plugin(self, source_path: str, server_path: str, install_method: str = "Manual", project_id: Optional[str] = None) -> bool:
        """Añade un plugin o mod local copiándolo al directorio correspondiente"""
        try:
            import shutil

            filename = os.path.basename(source_path)
            plugin_type = self._detect_plugin_type(source_path)

            if not plugin_type:
                self._log("Could not detect if the file is a plugin or a mod.\n")
                return False

            if plugin_type == "plugin":
                target_dir = os.path.join(server_path, "plugins")
            else:
                target_dir = os.path.join(server_path, "mods")

            os.makedirs(target_dir, exist_ok=True)

            target_path = os.path.join(target_dir, filename)
            shutil.copy2(source_path, target_path)

            # Guardar metadatos
            plugin_name = filename.replace('.jar', '')
            self._add_plugin_metadata(server_path, plugin_name, install_method, project_id, plugin_type)

            self._log(f"Added {plugin_type}: {filename} (Method: {install_method})\n")
            return True

        except Exception as e:
            self._log(f"Error adding plugin: {e}\n")
            return False
