"""
Base class for application plugins.
All plugins must inherit from BasePlugin and implement the required methods.
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from abc import ABC, abstractmethod
from typing import Optional


class BasePlugin(ABC):
    """
    Abstract base class for application plugins.
    
    Plugins extend the functionality of Minecraft Server Manager by adding
    new pages to the sidebar and providing custom UI and logic.
    
    To create a plugin:
      1. Create a directory under plugins/ with your plugin name
      2. Create an __init__.py that exports a class inheriting from BasePlugin
      3. Implement all abstract methods
    """

    def __init__(self):
        self._parent_window = None
        self._console_manager = None
        self._selected_server = None

    # ── Metadata (must be implemented) ─────────────────────────────────

    @property
    @abstractmethod
    def plugin_id(self) -> str:
        """Unique identifier for the plugin (e.g. 'git_manager')"""
        ...

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Human-readable name shown in the sidebar"""
        ...

    @property
    @abstractmethod
    def plugin_icon(self) -> str:
        """GTK icon name shown in the sidebar (e.g. 'utilities-terminal')"""
        ...

    @property
    def plugin_version(self) -> str:
        """Plugin version string"""
        return "1.0.0"

    @property
    def plugin_description(self) -> str:
        """Short description of the plugin"""
        return ""

    # ── Lifecycle ──────────────────────────────────────────────────────

    def activate(self, parent_window, console_manager):
        """
        Called when the plugin is activated.
        Receives references to the main window and console manager.
        """
        self._parent_window = parent_window
        self._console_manager = console_manager

    def deactivate(self):
        """Called when the plugin is deactivated."""
        pass

    # ── UI ─────────────────────────────────────────────────────────────

    @abstractmethod
    def create_page(self) -> Gtk.Widget:
        """
        Create and return the GTK widget for this plugin's page.
        This widget will be added to the main content stack.
        """
        ...

    # ── Server selection ───────────────────────────────────────────────

    def select_server(self, server):
        """Called when the user selects a different server."""
        self._selected_server = server

    # ── Helpers available to plugins ───────────────────────────────────

    def log(self, message: str):
        """Log a message to the application console."""
        if self._console_manager:
            self._console_manager.log_to_console(message)
