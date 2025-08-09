"""
Console Manager for the Minecraft Server Manager
Handles console output, logging, and auto-scroll functionality
"""
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class ConsoleManager:
    """Manages console functionality for the server manager"""
    
    def __init__(self):
        self.console_buffer = None
        self.console_view = None
        self.console_scrolled_window = None
        self.console_adjustment = None
        
    def setup_console_view(self, container):
        """Configura la vista de consola"""
        self.console_buffer = Gtk.TextBuffer()
        self.console_view = Gtk.TextView(buffer=self.console_buffer)
        self.console_view.set_editable(False)
        self.console_view.set_cursor_visible(False)

        self.console_scrolled_window = Gtk.ScrolledWindow()
        self.console_scrolled_window.set_hexpand(True)
        self.console_scrolled_window.set_vexpand(True)
        self.console_scrolled_window.add(self.console_view)
        container.pack_start(self.console_scrolled_window, True, True, 0)
        
        # Configurar auto-scroll
        self.console_adjustment = self.console_scrolled_window.get_vadjustment()
        
        return {
            'console_buffer': self.console_buffer,
            'console_view': self.console_view,
            'console_scrolled_window': self.console_scrolled_window
        }

    def log_to_console(self, message: str):
        """Añade un mensaje a la consola con auto-scroll"""
        if not self.console_buffer or not self.console_adjustment:
            return
            
        # Verificar si estamos al final
        at_bottom = False
        if self.console_adjustment.get_upper() > 0:
            current = self.console_adjustment.get_value()
            page_size = self.console_adjustment.get_page_size()
            upper = self.console_adjustment.get_upper()
            if current + page_size >= upper:
                at_bottom = True

        # Insertar texto
        self.console_buffer.insert_at_cursor(message)

        # Auto-scroll si estábamos al final
        if at_bottom:
            self.console_adjustment.set_value(self.console_adjustment.get_upper())

    def clear_console(self):
        """Limpia el contenido de la consola"""
        if self.console_buffer:
            self.console_buffer.set_text("")
            
    def get_console_text(self):
        """Obtiene todo el texto de la consola"""
        if self.console_buffer:
            start = self.console_buffer.get_start_iter()
            end = self.console_buffer.get_end_iter()
            return self.console_buffer.get_text(start, end, False)
        return ""
