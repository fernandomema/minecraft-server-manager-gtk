"""
Controlador para manejar descargas de servidores
"""
import json
import urllib.request
import urllib.parse
import threading
import os
from typing import List, Dict, Optional, Callable
from gi.repository import GLib

from utils.constants import PAPER_API_BASE_URL


class DownloadController:
    def __init__(self):
        self.download_callback: Optional[Callable[[str], None]] = None
        self.progress_callback: Optional[Callable[[str], None]] = None
    
    def set_download_callback(self, callback: Callable[[str], None]):
        """Establece el callback para mensajes de descarga"""
        self.download_callback = callback
    
    def set_progress_callback(self, callback: Callable[[str], None]):
        """Establece el callback para progreso de descarga"""
        self.progress_callback = callback
    
    def _log(self, message: str):
        """Envía un mensaje de log"""
        if self.download_callback:
            self.download_callback(message)
    
    def _progress(self, message: str):
        """Envía un mensaje de progreso"""
        if self.progress_callback:
            self.progress_callback(message)
    
    def get_paper_versions(self) -> List[str]:
        """Obtiene las versiones disponibles de PaperMC"""
        try:
            url = f"{PAPER_API_BASE_URL}/projects/paper"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                return data.get("versions", [])
        except Exception as e:
            self._log(f"Error fetching Paper versions: {e}\n")
            return []
    
    def get_paper_versions_async(self, callback: Callable[[List[str]], None]):
        """Obtiene las versiones de Paper de forma asíncrona"""
        def fetch_versions():
            versions = self.get_paper_versions()
            GLib.idle_add(callback, versions)
        
        threading.Thread(target=fetch_versions, daemon=True).start()
    
    def download_paper_jar(self, version: str, target_directory: str, 
                          success_callback: Optional[Callable[[str], None]] = None) -> bool:
        """Inicia la descarga de un JAR de PaperMC de forma asíncrona"""
        def download():
            try:
                self._log(f"Fetching build information for Paper {version}...\n")
                
                # Obtener el último build
                url = f"{PAPER_API_BASE_URL}/projects/paper/versions/{version}"
                with urllib.request.urlopen(url) as response:
                    data = json.loads(response.read().decode())
                    latest_build = data["builds"][-1]
                
                jar_filename = f"paper-{version}-{latest_build}.jar"
                download_url = f"{PAPER_API_BASE_URL}/projects/paper/versions/{version}/builds/{latest_build}/downloads/{jar_filename}"
                target_path = os.path.join(target_directory, jar_filename)
                
                self._log(f"Downloading {jar_filename}...\n")
                self._progress("Downloading...")
                
                urllib.request.urlretrieve(download_url, target_path)
                
                GLib.idle_add(self._log, f"Successfully downloaded {jar_filename}.\n")
                GLib.idle_add(self._progress, "Download completed!")
                
                if success_callback:
                    GLib.idle_add(success_callback, jar_filename)
                
            except Exception as e:
                GLib.idle_add(self._log, f"Error downloading PaperMC JAR: {e}\n")
                GLib.idle_add(self._progress, "Download failed!")
        
        threading.Thread(target=download, daemon=True).start()
        return True
