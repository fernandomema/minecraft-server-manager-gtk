"""
Modelo para representar plugins/mods
"""
from typing import Optional


class Plugin:
    def __init__(self, name: str, source: str = "Local", version: str = "Unknown", file_path: Optional[str] = None):
        self.name = name
        self.source = source  # "Local", "Modrinth", etc.
        self.version = version
        self.file_path = file_path
    
    def is_local(self) -> bool:
        """Verifica si el plugin es local"""
        return self.source == "Local"
    
    def __str__(self) -> str:
        return f"Plugin(name='{self.name}', source='{self.source}', version='{self.version}')"
