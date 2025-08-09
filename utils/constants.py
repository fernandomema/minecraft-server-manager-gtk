"""
Constantes utilizadas en la aplicación Minecraft Server Manager
"""
import os
from pathlib import Path

# Crear directorio de datos del usuario si no existe
USER_DATA_DIR = os.path.join(Path.home(), ".local", "share", "minecraft-server-manager")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# Archivos de configuración
SERVER_CONFIG_FILE = os.path.join(USER_DATA_DIR, "servers.json")

# Mensajes de error
EULA_ERROR_MESSAGE = "You need to agree to the EULA in order to run the server."

# URLs de APIs
PAPER_API_BASE_URL = "https://api.papermc.io/v2"
MODRINTH_API_BASE_URL = "https://api.modrinth.com/v2"

# Configuración de servidor por defecto
DEFAULT_JAVA_MEMORY = "1024M"
DEFAULT_JAR_ARGS = ["nogui"]

# Extensiones de archivos
JAR_EXTENSION = ".jar"
