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
from utils.file_utils import get_plugins_and_mods


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
    
    def get_local_plugins(self, server_path: str) -> List[Plugin]:
        """Obtiene la lista de plugins locales de un servidor"""
        plugins = []
        items = get_plugins_and_mods(server_path)
        
        for filename, full_path in items:
            plugin = Plugin(
                name=filename.replace('.jar', ''),
                source="Local",
                version="Unknown",
                file_path=full_path
            )
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
                self._log(f"Searching Modrinth for '{query}'...\n")
                
                encoded_query = urllib.parse.quote(query)
                url = f"{MODRINTH_API_BASE_URL}/search?query={encoded_query}&facets=[[\"project_type:mod\",\"project_type:plugin\"]]"
                
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                
                plugins = []
                if data and "hits" in data:
                    for hit in data["hits"]:
                        name = hit.get("title", "N/A")
                        version = "N/A"
                        if hit.get("game_versions"):
                            version = hit["game_versions"][0]
                        
                        plugin = Plugin(
                            name=name,
                            source="Modrinth",
                            version=version
                        )
                        plugins.append(plugin)
                    
                    GLib.idle_add(self._log, f"Found {len(plugins)} results from Modrinth.\n")
                else:
                    GLib.idle_add(self._log, "No results found from Modrinth.\n")
                
                GLib.idle_add(callback, plugins)
                
            except Exception as e:
                GLib.idle_add(self._log, f"Error searching Modrinth: {e}\n")
                GLib.idle_add(callback, [])
        
        threading.Thread(target=perform_search, daemon=True).start()
    
    def remove_local_plugin(self, plugin: Plugin) -> bool:
        """Elimina un plugin local"""
        if not plugin.is_local() or not plugin.file_path:
            self._log("Cannot remove non-local plugin or plugin without file path.\n")
            return False
        
        try:
            if os.path.exists(plugin.file_path):
                os.remove(plugin.file_path)
                self._log(f"Removed plugin: {plugin.name}\n")
                return True
            else:
                self._log(f"Plugin file not found: {plugin.file_path}\n")
                return False
        except Exception as e:
            self._log(f"Error removing plugin: {e}\n")
            return False
    
    def add_local_plugin(self, source_path: str, server_path: str) -> bool:
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
            self._log(f"Added plugin: {filename}\n")
            return True
            
        except Exception as e:
            self._log(f"Error adding plugin: {e}\n")
            return False
