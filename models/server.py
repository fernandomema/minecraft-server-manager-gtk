"""
Modelo para representar un servidor de Minecraft
"""
from typing import Optional, Dict, Any


class MinecraftServer:
    def __init__(self, name: str, path: str, jar: str,
                 resource_pack: str = "", resource_pack_sha1: str = ""):
        self.name = name
        self.path = path
        self.jar = jar
        self.resource_pack = resource_pack
        self.resource_pack_sha1 = resource_pack_sha1
        self.process = None
        self.is_running = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el servidor a diccionario para serialización"""
        return {
            "name": self.name,
            "path": self.path,
            "jar": self.jar,
            "resource_pack": self.resource_pack,
            "resource_pack_sha1": self.resource_pack_sha1
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MinecraftServer':
        """Crea un servidor desde un diccionario"""
        return cls(
            name=data.get("name", ""),
            path=data.get("path", ""),
            jar=data.get("jar", "DOWNLOAD_LATER"),
            resource_pack=data.get("resource_pack", ""),
            resource_pack_sha1=data.get("resource_pack_sha1", "")
        )
    
    def is_valid(self) -> bool:
        """Verifica si el servidor tiene datos válidos"""
        return bool(self.name and self.path)
    
    def has_jar_file(self) -> bool:
        """Verifica si el servidor tiene un archivo JAR válido"""
        return self.jar != "DOWNLOAD_LATER"
    
    def __str__(self) -> str:
        return f"MinecraftServer(name='{self.name}', path='{self.path}', jar='{self.jar}')"
