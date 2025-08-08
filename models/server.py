"""
Modelo para representar un servidor de Minecraft
"""
from typing import Optional, Dict, Any


class MinecraftServer:
    def __init__(self, name: str, path: str, jar: str):
        self.name = name
        self.path = path
        self.jar = jar
        self.process = None
        self.is_running = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el servidor a diccionario para serialización"""
        return {
            "name": self.name,
            "path": self.path,
            "jar": self.jar
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinecraftServer':
        """Crea un servidor desde un diccionario"""
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            jar=data.get("jar", "DOWNLOAD_LATER")
        )
    
    def is_valid(self) -> bool:
        """Verifica si el servidor tiene datos válidos"""
        return bool(self.name and self.path)
    
    def has_jar_file(self) -> bool:
        """Verifica si el servidor tiene un archivo JAR válido"""
        return self.jar != "DOWNLOAD_LATER"
    
    def __str__(self) -> str:
        return f"MinecraftServer(name='{self.name}', path='{self.path}', jar='{self.jar}')"
