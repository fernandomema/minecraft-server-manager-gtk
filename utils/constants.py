"""
Constantes utilizadas en la aplicación Minecraft Server Manager
"""
import os

# Archivos de configuración
SERVER_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "servers.json")

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
