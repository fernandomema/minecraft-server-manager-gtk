"""
Plugin Manager – discovers, loads, and manages application plugins.
"""
import os
import importlib
import traceback
from typing import List, Dict, Optional

from plugins.base_plugin import BasePlugin


class AppPluginManager:
    """
    Discovers and manages application plugins.
    
    Plugins are Python packages located under the ``plugins/`` directory.
    Each package must expose a top-level class that inherits from
    :class:`BasePlugin`.
    """

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    # ── Discovery & loading ────────────────────────────────────────────

    def discover_plugins(self) -> List[BasePlugin]:
        """
        Scan the ``plugins/`` directory for valid plugin packages and
        load them.  Returns the list of successfully loaded plugins.
        """
        plugins_dir = os.path.dirname(os.path.abspath(__file__))
        loaded: List[BasePlugin] = []

        for entry in sorted(os.listdir(plugins_dir)):
            entry_path = os.path.join(plugins_dir, entry)
            # Only consider sub-directories that look like Python packages
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith("_"):
                continue
            init_file = os.path.join(entry_path, "__init__.py")
            if not os.path.isfile(init_file):
                continue

            try:
                module = importlib.import_module(f"plugins.{entry}")
                # Find the first BasePlugin subclass exported by the module
                plugin_class = self._find_plugin_class(module)
                if plugin_class is None:
                    print(f"[PluginManager] No BasePlugin subclass found in plugins.{entry}")
                    continue

                instance = plugin_class()
                self._plugins[instance.plugin_id] = instance
                loaded.append(instance)
                print(f"[PluginManager] Loaded plugin: {instance.plugin_name} "
                      f"(v{instance.plugin_version})")
            except Exception:
                print(f"[PluginManager] Failed to load plugin '{entry}':")
                traceback.print_exc()

        return loaded

    @staticmethod
    def _find_plugin_class(module):
        """Return the first BasePlugin subclass defined in *module*."""
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type)
                    and issubclass(attr, BasePlugin)
                    and attr is not BasePlugin):
                return attr
        return None

    # ── Access ─────────────────────────────────────────────────────────

    def get_plugins(self) -> List[BasePlugin]:
        """Return all loaded plugins."""
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[BasePlugin]:
        """Return a specific plugin by id, or ``None``."""
        return self._plugins.get(plugin_id)

    # ── Lifecycle helpers ──────────────────────────────────────────────

    def activate_all(self, parent_window, console_manager):
        """Activate every loaded plugin."""
        for plugin in self._plugins.values():
            try:
                plugin.activate(parent_window, console_manager)
            except Exception:
                print(f"[PluginManager] Error activating {plugin.plugin_id}:")
                traceback.print_exc()

    def deactivate_all(self):
        """Deactivate every loaded plugin."""
        for plugin in self._plugins.values():
            try:
                plugin.deactivate()
            except Exception:
                print(f"[PluginManager] Error deactivating {plugin.plugin_id}:")
                traceback.print_exc()

    def select_server_all(self, server):
        """Notify every plugin about a server selection change."""
        for plugin in self._plugins.values():
            try:
                plugin.select_server(server)
            except Exception:
                print(f"[PluginManager] Error in {plugin.plugin_id}.select_server:")
                traceback.print_exc()
