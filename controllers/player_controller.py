"""
PlayerController for managing player lists in Minecraft servers.
Handles reading and writing of whitelist, operators, and banned player files.
"""
import os
from typing import List, Optional

from models.server import MinecraftServer
from utils.file_utils import load_json_file, save_json_file


class PlayerController:
    """Controller to manage player-related files"""

    def __init__(self):
        self.server: Optional[MinecraftServer] = None
        self.online_players: List[str] = []

    def set_server(self, server: MinecraftServer):
        """Set the current server for player operations"""
        self.server = server

    def set_online_players(self, players: List[str]):
        """Update the list of online players"""
        self.online_players = players.copy()

    def get_online_players(self) -> List[str]:
        """Return the list of online players"""
        return self.online_players.copy()

    # Helper methods
    def _get_file_path(self, filename: str) -> Optional[str]:
        if not self.server:
            return None
        return os.path.join(self.server.path, filename)

    # Whitelist management
    def get_whitelist(self) -> List[str]:
        """Load whitelist entries"""
        path = self._get_file_path("whitelist.json")
        if not path:
            return []
        data = load_json_file(path)
        return [entry.get("name", "") for entry in data]

    def add_to_whitelist(self, name: str) -> bool:
        """Add a player to the whitelist"""
        path = self._get_file_path("whitelist.json")
        if not path:
            return False
        data = load_json_file(path)
        if not any(entry.get("name") == name for entry in data):
            data.append({"name": name})
            return save_json_file(path, data)
        return False

    def remove_from_whitelist(self, name: str) -> bool:
        """Remove a player from the whitelist"""
        path = self._get_file_path("whitelist.json")
        if not path:
            return False
        data = load_json_file(path)
        new_data = [entry for entry in data if entry.get("name") != name]
        return save_json_file(path, new_data)

    # Operators management
    def get_operators(self) -> List[str]:
        """Load operator entries"""
        path = self._get_file_path("ops.json")
        if not path:
            return []
        data = load_json_file(path)
        return [entry.get("name", "") for entry in data]

    def add_operator(self, name: str, level: int = 4) -> bool:
        """Add an operator"""
        path = self._get_file_path("ops.json")
        if not path:
            return False
        data = load_json_file(path)
        if not any(entry.get("name") == name for entry in data):
            data.append({"name": name, "level": level})
            return save_json_file(path, data)
        return False

    def remove_operator(self, name: str) -> bool:
        """Remove an operator"""
        path = self._get_file_path("ops.json")
        if not path:
            return False
        data = load_json_file(path)
        new_data = [entry for entry in data if entry.get("name") != name]
        return save_json_file(path, new_data)

    # Banned players management
    def get_banned_players(self) -> List[str]:
        """Load banned players"""
        path = self._get_file_path("banned-players.json")
        if not path:
            return []
        data = load_json_file(path)
        return [entry.get("name", "") for entry in data]

    def add_banned_player(self, name: str, reason: str = "Banned") -> bool:
        """Ban a player"""
        path = self._get_file_path("banned-players.json")
        if not path:
            return False
        data = load_json_file(path)
        if not any(entry.get("name") == name for entry in data):
            data.append({"name": name, "reason": reason})
            return save_json_file(path, data)
        return False

    def remove_banned_player(self, name: str) -> bool:
        """Unban a player"""
        path = self._get_file_path("banned-players.json")
        if not path:
            return False
        data = load_json_file(path)
        new_data = [entry for entry in data if entry.get("name") != name]
        return save_json_file(path, new_data)
