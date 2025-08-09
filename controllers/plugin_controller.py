"""
Controlador para manejar plugins y mods
"""
import json
import urllib.request
import urllib.parse
import threading
import os
from typing import List, Dict, Optional, Callable
from gi.repository import GLib

from models.plugin import Plugin
from utils.constants import MODRINTH_API_BASE_URL
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
    
    def _get_plugin_metadata_file(self, server_path: str) -> str:
        """Obtiene la ruta del archivo de metadatos de plugins"""
        return os.path.join(server_path, ".plugin_metadata.json")
    
    def _load_plugin_metadata(self, server_path: str) -> Dict[str, Dict]:
        """Carga los metadatos de plugins de un servidor"""
        metadata_file = self._get_plugin_metadata_file(server_path)
        try:
            return load_json_file(metadata_file) if os.path.exists(metadata_file) else {}
        except Exception:
            return {}
    
    def _save_plugin_metadata(self, server_path: str, metadata: Dict[str, Dict]) -> bool:
        """Guarda los metadatos de plugins de un servidor"""
        metadata_file = self._get_plugin_metadata_file(server_path)
        try:
            return save_json_file(metadata_file, metadata)
        except Exception as e:
            self._log(f"Error saving plugin metadata: {e}\n")
            return False
    
    def _add_plugin_metadata(self, server_path: str, plugin_name: str, install_method: str, project_id: Optional[str] = None):
        """Añade metadatos para un plugin"""
        metadata = self._load_plugin_metadata(server_path)
        metadata[plugin_name] = {
            "install_method": install_method,
            "project_id": project_id,
            "installed_at": __import__("datetime").datetime.now().isoformat()
        }
        self._save_plugin_metadata(server_path, metadata)
    
    def _remove_plugin_metadata(self, server_path: str, plugin_name: str):
        """Elimina metadatos de un plugin"""
        metadata = self._load_plugin_metadata(server_path)
        if plugin_name in metadata:
            del metadata[plugin_name]
            self._save_plugin_metadata(server_path, metadata)
    
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
            
            plugin = Plugin(
                name=plugin_name,
                source="Local",
                version="Unknown",
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
    
    def search_modrinth_plugins(self, query: str, callback: Callable[[List[Plugin]], None]):
        """Busca plugins en Modrinth de forma asíncrona"""
        def perform_search():
            try:
                self._log(f"DEBUG: Starting Modrinth search thread for '{query}'.\n")
                
                encoded_query = urllib.parse.quote(query)
                # Usar una versión simplificada de la API primero para probar
                url = f"{MODRINTH_API_BASE_URL}/search?query={encoded_query}"
                
                self._log(f"DEBUG: Modrinth API URL: {url}\n")
                
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 'MinecraftServerManager/1.0')
                
                with urllib.request.urlopen(request) as response:
                    data = json.loads(response.read().decode())
                
                self._log(f"DEBUG: Received response from Modrinth API.\n")
                
                plugins = []
                if data and "hits" in data:
                    self._log(f"DEBUG: Processing {len(data['hits'])} hits from API.\n")
                    for hit in data["hits"]:
                        # Filtrar solo plugins y mods
                        project_type = hit.get("project_type", "").lower()
                        if project_type not in ["mod", "plugin"]:
                            continue
                            
                        name = hit.get("title", "N/A")
                        description = hit.get("description", "")[:200] + "..." if len(hit.get("description", "")) > 200 else hit.get("description", "")
                        version = "Latest"
                        if hit.get("versions"):
                            version = hit["versions"][0] if hit["versions"] else "Latest"
                        
                        plugin = Plugin(
                            name=name,
                            source="Modrinth",
                            version=version,
                            description=description
                        )
                        # Añadir el tipo de proyecto como atributo
                        plugin.project_type = project_type
                        plugins.append(plugin)
                    
                    GLib.idle_add(self._log, f"Found {len(plugins)} plugins/mods from Modrinth.\n")
                else:
                    GLib.idle_add(self._log, "No results found from Modrinth.\n")
                
                GLib.idle_add(callback, plugins)
                
            except urllib.error.HTTPError as e:
                GLib.idle_add(self._log, f"DEBUG: HTTP Error {e.code}: {e.reason}\n")
                GLib.idle_add(callback, [])
            except urllib.error.URLError as e:
                GLib.idle_add(self._log, f"DEBUG: URL Error: {e.reason}\n")
                GLib.idle_add(callback, [])
            except Exception as e:
                GLib.idle_add(self._log, f"DEBUG: Error searching Modrinth: {e}\n")
                GLib.idle_add(callback, [])
        
        threading.Thread(target=perform_search, daemon=True).start()
    
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
        """Añade un plugin local copiándolo al directorio de plugins del servidor"""
        try:
            import shutil
            
            # Determinar directorio de destino (plugins o mods)
            plugins_dir = os.path.join(server_path, "plugins")
            mods_dir = os.path.join(server_path, "mods")
            
            # Crear directorio plugins si no existe
            os.makedirs(plugins_dir, exist_ok=True)
            
            filename = os.path.basename(source_path)
            target_path = os.path.join(plugins_dir, filename)
            
            shutil.copy2(source_path, target_path)
            
            # Guardar metadatos
            plugin_name = filename.replace('.jar', '')
            self._add_plugin_metadata(server_path, plugin_name, install_method, project_id)
            
            self._log(f"Added plugin: {filename} (Method: {install_method})\n")
            return True
            
        except Exception as e:
            self._log(f"Error adding plugin: {e}\n")
            return False
