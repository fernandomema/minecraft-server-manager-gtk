"""
Modelo para representar plugins/mods
"""
from typing import Optional


class Plugin:
    def __init__(self, name: str, source: str = "Local", version: str = "Unknown", file_path: Optional[str] = None, description: str = "", install_method: str = "Manual"):
        self.name = name
        self.source = source  # "Local", "Modrinth", etc.
        self.version = version
        self.file_path = file_path
        self.description = description
        self.install_method = install_method  # "Manual", "Modrinth", "CurseForge", etc.
        self.project_id = None  # ID del proyecto en la fuente externa (para actualizaciones)
    
    def is_local(self) -> bool:
        """Verifica si el plugin es local"""
        return self.source == "Local"
    
    def is_managed(self) -> bool:
        """Verifica si el plugin está gestionado por una fuente externa"""
        return self.install_method != "Manual"
    
    def can_be_updated(self) -> bool:
        """Verifica si el plugin puede ser actualizado automáticamente"""
        return self.is_managed() and self.project_id is not None
    
    def get_install_method_display(self) -> str:
        """Obtiene el texto a mostrar para el método de instalación"""
        if self.install_method == "Manual":
            return "Manual"
        elif self.install_method == "Modrinth":
            return "🌐 Modrinth"
        elif self.install_method == "Spigot":
            return "🟠 Spigot"
        elif self.install_method == "CurseForge":
            return "🔥 CurseForge"
        else:
            return f"📦 {self.install_method}"
    
    def __str__(self) -> str:
        return f"Plugin(name='{self.name}', source='{self.source}', version='{self.version}')"
