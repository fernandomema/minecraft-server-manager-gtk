"""
Controlador para manejar servidores de Minecraft
"""
import subprocess
import threading
import time
import os
from typing import List, Dict, Optional, Callable
from gi.repository import GLib

from models.server import MinecraftServer
from utils.constants import SERVER_CONFIG_FILE, EULA_ERROR_MESSAGE, DEFAULT_JAVA_MEMORY, DEFAULT_JAR_ARGS
from utils.file_utils import load_json_file, save_json_file


class ServerController:
    def __init__(self):
        self.servers: List[MinecraftServer] = []
        self.running_servers: Dict[str, subprocess.Popen] = {}
        self.console_callback: Optional[Callable[[str], None]] = None
        self.server_finished_callback: Optional[Callable[[str, int], None]] = None
        self.eula_dialogs_active = set()
    
    def set_console_callback(self, callback: Callable[[str], None]):
        """Establece el callback para mostrar mensajes en la consola"""
        self.console_callback = callback
    
    def set_server_finished_callback(self, callback: Callable[[str, int], None]):
        """Establece el callback para cuando un servidor termina"""
        self.server_finished_callback = callback
    
    def _log(self, message: str):
        """Envía un mensaje a la consola si hay callback configurado"""
        if self.console_callback:
            self.console_callback(message)
    
    def load_servers(self) -> bool:
        """Carga la configuración de servidores desde archivo"""
        try:
            servers_data = load_json_file(SERVER_CONFIG_FILE)
            self.servers = [MinecraftServer.from_dict(data) for data in servers_data]
            self._log(f"Loaded {len(self.servers)} servers from configuration.\n")
            return True
        except Exception as e:
            self._log(f"Error loading servers: {e}\n")
            return False
    
    def save_servers(self) -> bool:
        """Guarda la configuración de servidores a archivo"""
        try:
            servers_data = [server.to_dict() for server in self.servers]
            success = save_json_file(SERVER_CONFIG_FILE, servers_data)
            if success:
                self._log("Server configurations saved.\n")
            else:
                self._log("Error saving server configurations.\n")
            return success
        except Exception as e:
            self._log(f"Error saving servers: {e}\n")
            return False
    
    def add_server(self, name: str, path: str, jar: str = "DOWNLOAD_LATER") -> bool:
        """Añade un nuevo servidor"""
        if not name or not path:
            self._log("Server name or path cannot be empty.\n")
            return False
        
        server = MinecraftServer(name, path, jar)
        self.servers.append(server)
        self._log(f"Added server: {name} at {path} using {jar}\n")
        return self.save_servers()
    
    def get_servers(self) -> List[MinecraftServer]:
        """Obtiene la lista de servidores"""
        return self.servers.copy()
    
    def find_server_by_name(self, name: str) -> Optional[MinecraftServer]:
        """Busca un servidor por nombre"""
        for server in self.servers:
            if server.name == name:
                return server
        return None
    
    def find_server_by_path(self, path: str) -> Optional[MinecraftServer]:
        """Busca un servidor por ruta"""
        for server in self.servers:
            if server.path == path:
                return server
        return None

    def get_logs_directory(self, server: MinecraftServer) -> str:
        """Obtiene la ruta del directorio de logs para un servidor"""
        return os.path.join(server.path, "logs")

    def get_available_log_files(self, server: MinecraftServer) -> List[str]:
        """Devuelve una lista de rutas de archivos de log disponibles"""
        logs_dir = self.get_logs_directory(server)
        if not os.path.isdir(logs_dir):
            return []

        log_files = []
        for filename in sorted(os.listdir(logs_dir)):
            if filename.endswith(".log") or filename.endswith(".log.gz"):
                log_files.append(os.path.join(logs_dir, filename))
        return log_files
    
    def is_server_running(self, server: MinecraftServer) -> bool:
        """Verifica si un servidor está ejecutándose"""
        return server.path in self.running_servers
    
    def start_server(self, server: MinecraftServer) -> bool:
        """Inicia un servidor"""
        if not server.has_jar_file():
            self._log("Please download a server JAR first or select an existing one.\n")
            return False
        
        if self.is_server_running(server):
            self._log(f"Server '{server.name}' is already running.\n")
            return False
        
        # Verificar EULA antes de iniciar
        if not self._check_eula(server):
            return False
        
        full_jar_path = os.path.join(server.path, server.jar)
        if not os.path.exists(full_jar_path):
            self._log(f"Error: Server JAR not found at '{full_jar_path}'. Please check the path.\n")
            return False
        
        try:
            self._log(f"Starting server '{server.name}' using {server.jar}...\n")
            
            process = subprocess.Popen(
                ["java", f"-Xmx{DEFAULT_JAVA_MEMORY}", f"-Xms{DEFAULT_JAVA_MEMORY}", 
                 "-jar", server.jar] + DEFAULT_JAR_ARGS,
                cwd=server.path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.running_servers[server.path] = process
            server.process = process
            server.is_running = True
            
            self._log(f"Server '{server.name}' started. PID: {process.pid}\n")
            
            # Iniciar hilos para leer salida
            threading.Thread(target=self._read_stdout, args=(process, server), daemon=True).start()
            threading.Thread(target=self._read_stderr, args=(process, server), daemon=True).start()
            threading.Thread(target=self._monitor_process, args=(process, server), daemon=True).start()
            
            return True
            
        except Exception as e:
            self._log(f"Failed to start server: {e}\n")
            return False
    
    def stop_server(self, server: MinecraftServer) -> bool:
        """Detiene un servidor de forma elegante"""
        process = self.running_servers.get(server.path)
        if not process:
            self._log(f"Server '{server.name}' is not running.\n")
            return False
        
        try:
            self._log(f"Stopping server '{server.name}'...\n")
            process.stdin.write("stop\n")
            process.stdin.flush()
            return True
        except Exception as e:
            self._log(f"Error sending stop command: {e}. Terminating process.\n")
            return self.kill_server(server)
    
    def kill_server(self, server: MinecraftServer) -> bool:
        """Termina un servidor de forma forzada"""
        process = self.running_servers.get(server.path)
        if not process:
            self._log(f"Server '{server.name}' is not running.\n")
            return False
        
        try:
            self._log(f"Forcefully terminating server '{server.name}'...\n")
            process.terminate()
            return True
        except Exception as e:
            self._log(f"Error terminating server: {e}\n")
            return False
    
    def _check_eula(self, server: MinecraftServer) -> bool:
        """Verifica el estado del EULA"""
        eula_file_path = os.path.join(server.path, "eula.txt")
        if os.path.exists(eula_file_path):
            try:
                with open(eula_file_path, "r") as f:
                    eula_content = f.read()
                if "eula=false" in eula_content:
                    self._log(f"EULA not accepted for server '{server.name}'. Please accept EULA first.\n")
                    return False
            except Exception as e:
                self._log(f"Error reading eula.txt: {e}\n")
                return False
        return True
    
    def accept_eula(self, server: MinecraftServer) -> bool:
        """Acepta el EULA para un servidor"""
        eula_file_path = os.path.join(server.path, "eula.txt")
        try:
            if os.path.exists(eula_file_path):
                with open(eula_file_path, "r") as f:
                    lines = f.readlines()
                with open(eula_file_path, "w") as f:
                    for line in lines:
                        if line.strip() == "eula=false":
                            f.write("eula=true\n")
                        else:
                            f.write(line)
            else:
                # Crear archivo EULA si no existe
                with open(eula_file_path, "w") as f:
                    f.write("#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://account.mojang.com/documents/minecraft_eula).\n")
                    f.write("eula=true\n")
            
            self._log(f"EULA accepted for server '{server.name}'.\n")
            return True
        except Exception as e:
            self._log(f"Error accepting EULA: {e}\n")
            return False
    
    def update_server_jar(self, server: MinecraftServer, jar_filename: str) -> bool:
        """Actualiza el archivo JAR de un servidor"""
        server.jar = jar_filename
        return self.save_servers()
    
    def remove_server(self, server: MinecraftServer) -> bool:
        """Elimina un servidor de la lista (sin eliminar archivos)"""
        try:
            if server in self.servers:
                # Detener el servidor si está ejecutándose
                if self.is_server_running(server):
                    self.kill_server(server)
                
                self.servers.remove(server)
                self._log(f"Server '{server.name}' removed from management.\n")
                return self.save_servers()
            return False
        except Exception as e:
            self._log(f"Error removing server: {e}\n")
            return False
    
    def _read_stdout(self, process: subprocess.Popen, server: MinecraftServer):
        """Lee la salida estándar del proceso"""
        try:
            for line in process.stdout:
                GLib.idle_add(self._log, line)
                if EULA_ERROR_MESSAGE in line and server.path not in self.eula_dialogs_active:
                    self.eula_dialogs_active.add(server.path)
                    # Aquí se podría emitir una señal para mostrar diálogo EULA
        except Exception as e:
            GLib.idle_add(self._log, f"Error reading stdout: {e}\n")
    
    def _read_stderr(self, process: subprocess.Popen, server: MinecraftServer):
        """Lee la salida de error del proceso"""
        try:
            for line in process.stderr:
                GLib.idle_add(self._log, f"[STDERR] {line}")
                if EULA_ERROR_MESSAGE in line and server.path not in self.eula_dialogs_active:
                    self.eula_dialogs_active.add(server.path)
                    # Aquí se podría emitir una señal para mostrar diálogo EULA
        except Exception as e:
            GLib.idle_add(self._log, f"Error reading stderr: {e}\n")
    
    def _monitor_process(self, process: subprocess.Popen, server: MinecraftServer):
        """Monitorea el proceso del servidor"""
        process.wait()
        GLib.idle_add(self._on_server_finished, server, process.returncode)
    
    def _on_server_finished(self, server: MinecraftServer, exit_code: int):
        """Maneja cuando un servidor termina"""
        if server.path in self.running_servers:
            del self.running_servers[server.path]
        
        server.process = None
        server.is_running = False
        
        if server.path in self.eula_dialogs_active:
            self.eula_dialogs_active.remove(server.path)
        
        self._log(f"Server '{server.name}' stopped. Exit code: {exit_code}\n")
        
        if self.server_finished_callback:
            self.server_finished_callback(server.path, exit_code)
